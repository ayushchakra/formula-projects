# CAN Software Update (aka Bootloader)

# Background

The CAN Software Updater is a system that allows engineers to flash new firmware onto an Electronic Control Unit (embedded system that controls a subsystem) using the CAN bus. Historically, boards had to be flashed one by one using a 6-pin programmer, like the USBasp, which operates using SPI. The programmer had to moved from one board to another, often requiring engineers to open an enclosure, which was especially cumbersome for boards located in the service section of the accumulator.

Purpose: Easier physically to flash boards.

## Background Knowledge

The following sections are descriptions of the major concepts used by the CAN Software Updater. The information is not specific to the CAN Software Updater.

### Memory layout of ATMega16m1

The ATMega16m1 has 3 different types of memory:


1. **Flash** (also known as NVM or non-volatile memory)

   
   1. Data persists through power cycle
   2. Large (16KB) and cheap
2. **RAM** (random access memory)

   
   1. Data is lost across power cycle
   2. Medium size (4KB), more expensive than flash
3. **EEPROM** (electrically erasable and programmable read-only memory)

   
   1. Data persists through power cycle
   2. Very small (512B)

//what would you wnat in eeprom vs flash

These blocks of memory are separate blocks within the die of the microcontroller, and are made of different types of silicon, which impacts their volatility and their price.

When programming or flashing a microcontroller, the program data (the CPU instructions, the data) are written to flash. This is the section of memory that we need to write during a software update.

RAM is used for data that is accessed during the runtime of a program, and is divided into a few different types, like stack and `const`.

EEPROM is much smaller than the other two sections of memory. EEPROM is often used for things like storing configurations, calibrations, and serial numbers. It can be written independently of flash, can be read and written during runtime, and persisted across resets.

### Bootloader

Flash memory in the ATMega16m1 is divided into two sections with configurable sizes: the *app section* and the *bootloader section*. The app section starts at memory address `0x0000`. The bootloader size is configurable, from 0KB (no bootloader) to 4KB. The main difference between the two sections is their abilities: code located in the bootloader section is able to read and write code in the app section, but code in the app section cannot.

It is useful to think of the chip as being able to host two different programs: the main application (like a blinky program or the BMS firmware) and the bootloader program. Each has its own `main()` function. They are not run at the same time though, because there is only 1 CPU, and there is no need to run them simultaneously.

// two main functions, do we manually have to pick which program is run? or does it default to one during specific cases, like during a drive it defaults to app program?
   // i think answered below, defaults to bootloader and if no update signalled, then it jumps to the application

### Writing to flash

As mentioned before, the bootloader is able to read and write flash memory in the application section—this is how we are able to perform a software update. Flash memory is divided up into *pages* of 256 bytes or 128 *words* each. Flash is written in a page-by-page fashion. First, a temporary page buffer is filled with the new contents of the page. Then, a page erase is performed. Finally, the temporary page buffer is written in one action to flash memory.

// maybe draw this out for me? what I think it is is the new data is saved as a page buffer, the old data is erased page by page, and then the buffer takes its place

Because flash is written page-by-page, and the page size is 256 bytes, this creates a challenge when using CAN because each CAN message is only 8 bytes, so we can't write the flash after each CAN message—we can only write after each set of 32 CAN messages, and we must internally keep track of the size and remaining capacity of the temporary page buffer so that we ensure the CAN messages are filling in the correct place.

### CAN

CAN, or controller area network, is a communication protocol used widely in automobiles. It operates with a bus topology, with nodes attached along the bus. Two wires that form a differential pair are used to transmit CAN frames, which consist of, among other things, a message ID, a data body, and a CRC check to verify the correctness of the message. The software updater makes use of CAN as the transport layer of its protocol, meaning that it uses CAN messages to convey information that is parsed into commands and packed into responses.

# Software Update

This section discusses the architecture of the CAN Software Updater. It will cover the 3 elements of the system: the bootloader, protocol, and updater client, then dive deep into various aspects of the architecture.

## Structure

As mentioned previously, the system is broken up into 3 elements: the bootloader, the protocol, and the client. The following three subsections will discuss them at length.

 ![](/api/attachments.redirect?id=0baef89b-4f05-4a3a-a04c-25a873242e64)

### Bootloader

The bootloader is the part of the system located within the target device (the device to be updated). It is an application that is responsible for listening for CAN messages, parsing them according to the protocol below, performing the necessary actions, and responding back over CAN to the client.

The bootloader occupies 4 out of the 16 kilobytes total flash memory for the ATMega16m1, and begins at memory address `0x3000`. The device's fuses will be reconfigured so that the bootloader is the first code to execute (so that the *reset vector* points to the start of the bootloader section). This is so that if a CAN software update fails and we power cycle the board, we don't start executing bad code—we just run the bootloader which allows us to try the update again.

// what's a reset vector, whats a fuse
// why is reset vector in nvm, not eeprom?

For normal execution (not performing an update) the bootloader will see that there was no update requested, and jump to the application. If an update *is* requested, as indicated by a bit set in the EEPROM memory, the bootloader will then move into the "updater" phase, in which it initializes the CAN peripheral and begins listening for CAN messages. The actions taken by the bootloader in response to the CAN messages will be discussed in the **Updater Protocol** section that follows.

//eeprom is changed electrically - does that mean CAN changes eeprom data if an update is requested?

After performing an update, the bootloader also performs validation of the image. There are two different methods used: image magic and a cyclic redundancy check. The image magic is a 4-byte field in the **Image Header** (discussed at length later) that should always be `OEM!` in hexadecimal. This is effectively the "trademark" for the team, so we won't execute any code that doesn't start with that. The cyclic redundancy check is a method to make sure that the image that was written to flash was written correctly. The **Client** transmits the CRC that *it* computed to the bootloader, and the bootloader also calculates its *own* CRC for the image. If the two are the same, then the image is valid and can be executed. If not, the image is invalid and won't be executed.

When compiling the bootloader, there is not much different than compiling a normal application, with one exception. When compiling the bootloader with `avr-gcc`, we must pass an additional flag to the linker: `-Wl,--section-start=.text=0x3000`. `-Wl` indicates to `avr-gcc` that the following flag should be passed to the linker `avr-ld`, and the flag itself tells the linker that the `.text` section, where the machine code/assembly is located, should start at address `0x3000`. That way, when we translate compiled ELF into a HEX file, the addresses start at `0x3000`, and when we flash using `avrdude`, it knows where to place the code.

// avr gcc is just a compiler that converts C to binary
// whats avr ld
// ELF - executable and linkable format

### Updater Protocol

The updater protocol is the set of commands and responses defined by the CAN Software Updater system communicated between the client and the target. The commands are implemented as CAN messages, utilizing the message ID as the command identifier and the body of the message to specify arguments. The commands follow:

| Command | ID | Type | Body |
|----|----|----|----|
| PING | 0x00 | COMMAND | No body (DLC=0) |
| SESSION | 0x02 | COMMAND | 1-byte of session-type (upload/download), 2-byte image size if upload. |
| DATA | 0x04 | COMMAND | 1-8 bytes of data from the binary |
| RESET | 0x06 | COMMAND | 1 byte for either set bootflag or clear bootflag |
| PING_ACK | 0x01 | RESPONSE | 1 byte bootloader version, 1 byte chip/arch ID (i.e. ATMega16m1 or STM32F103C8T6) |
| SESSION_ACK | 0x03 | RESPONSE | TBD |
| DATA_ACK | 0x05 | RESPONSE | 2 byte next address to program, 2 byte data expected remaining |
| RESET_ACK | 0x07 | RESPONSE | 1 byte response message: image is valid or image is invalid and reason. |
| QUERY_ALL | 0x0F | COMMAND | No body (DLC=0) |

// don't really understand this table, what is being sent and received? initial thought is command is sent from device controlling the update to the device being updated and then the response is returned

CAN message IDs are 11 bits. We can construct the full message ID by using the upper 7 bits as an ECU ID, and the lower 4 bits as the bootloader command ID. So if we want to update the Dashboard ECU which might have ID `0x12`, we can query using the CAN ID `0x120`, and if we want to reset it, we can send CAN ID `0x126`.

The CAN ID **TODO** `0x3FF` is reserved as the "query broadcast", which allows an updater to ping all of the available devices. When receiving this command, ECUs should respond with their message ID so that the client can tell which devices are on the network.

// is this just a connection/road kill harness check? also why this id

### Client

The updater client is a command-line tool written in C. The usage of the tool will be described below—this section describes the organization of the client code.

The CLI `main()` function is found in `client/main.c`. First, the arguments are parsed. If the `-v` or `--verbose` flag is passed, logging will be enabled. Eventually we can add support for environment variables that can set `LOG_LEVEL=info` (or `warning` or `error`) to dynamically set log level. The command (either `ping` or `flash`) is then parsed from the command line and the data is passed to a handling function found in `client/can_client.c`, which handles the command and interacting with the SocketCAN peripheral. As of now, the client is only supported on Linux.

// log level is what to log? like only log warnings or errors?

The commands sent by the client in response to the invocation by the command line are detailed in the next section, **Activity Flow**.

## Activity Flow

### Ping

###  ![](/api/attachments.redirect?id=4f68d30b-6d2f-4f52-a7b1-0c79a6dafca0)Flash

 ![](/api/attachments.redirect?id=6eac122e-73e3-4988-874d-fd758405ee93)

// what if ack is never sent? infinite loop?

## EEPROM Shared Memory

The EEPROM peripheral is used to share memory between the bootloader and the application. The primary use for the memory is a *bootflag*, which is used to indicate whether an update has been requested. When a MCU first boots up, it will start executing the bootloader at address `0x3000`. During normal operation, the bootloader needs to just jump to the application at address `0x0000`. But we also need to have some way of indicating that the bootloader should continue into the updater. This method needs to be accessible from the application because we need to be able to send a CAN message during runtime to indicate that we should go into the updater. It also needs to be accessible from the bootloader so that it can check to see if an update was requested and either jump to the application or continue and do an update.

// how is the data in the EEPROM structured? what dictates which bit signified the update signal?

RAM doesn't work for this purpose because it is ephemeral and resets after the board resets. Flash doesn't work because the application can't write to flash. Both the application and the bootloader can read and write EEPROM, and it is nonvolatile, which satisfies our needs. In `lib/shared_memory.c` there are functions to get and set the bootflag. If the bootflag `UPDATE_REQUESTED` is set to `1`, then the bootloader will go into updater mode. If it is set to `0`, the bootloader will jump to the application after determining that it is safe to do so (the CRC matches).

The CAN RESET command has an argument to set or clear the bootflag. When the device is executing the normal application and receives the CAN RESET command and indicates that it should be an "update reset", the application will set the `UPDATE_REQUESTED` bootflag in EEPROM and jump to the bootloader `0x3000`, which will then see the flag and continue into the updater.

## Image Header and Validation

The image header is a struct of metadata that is prepended to each executable:

```javascript
typedef struct image_hdr_t {
    uint32_t image_magic;      // Always "OEM!" ASCII codes
    uint32_t crc;              // 32-bit CRC of the application payload
    uint16_t image_size;       // Size of the app payload
    uint64_t flash_timestamp;  // Unix timestamp of when the image was flashed
    uint32_t reserved;         // Reserved for future use
    char git_sha[8];           // 8-byte git sha of the HEAD from which this was flashed
};
```

// why is the timestamp helpful? another check to make sure a flash went through?

The CRC is used by the bootloader as a comparison point: the bootloader can perform the same CRC check and compare it with the image header's CRC, and if they are the same, then the image is valid. The image header CRC is computed by the computer that compiles the code.

The flash timestamp is used to check and see when the code was flashed, which can be useful in debugging.

The image header will be defined by the application (automatically linked during compilation):

```javascript
image_hdr_t image_hdr __attribute__((section(".image_hdr"))) {
		.image_magic = IMAGE_MAGIC, // Constant predefined
		.git_sha = GIT_SHA,         // Defined during compilation
};
```

// is this what checks if the image generated by the ecu is the same as the one compiled by the computer? also dont understand this notation

The `__attribute__((section(".image_hdr")))` is a C attribute label that instructs the linker to place this struct in the section `.image_hdr` in the linker script. This is a custom section that was added to the default AVR linker script:

```javascript
SECTIONS
{
	.image_hdr :          // Defines a new section for code to be placed
	{
		__image_hdr = .;    // Defines a variable that can be accessed that hold the address of this section
		KEEP(*(.image_hdr)) // Instructs this section to contain anything with the label above
	} > text              // This section is located in the text section, as opposed to the data section
	...
}
```

// is image always a set size because always OEM!? whereas CRC is variable bc it changes based on the instance
// wait whats image header?

Since the `.image_hdr` section is at the beginning of the linker script, the linker will place it before any other code. This means that instead of the application being located at address `0x0000`, it is actually located at `0x0000 + sizeof(image_hdr_t)`, which is **TODO** `0x0030`.

Because the image size and CRC aren't known during the linking stage of compilation, a script is needed to patch the header after compiling. This script is found in `scripts/patch_header.c`. The script checks to ensure that the image magic value is correct, computes the CRC and the image size, and adds the values into the binary directly. This script will eventually be parameterized to be invoked by an application to patch individual parts directly.

# Client Usage

This section goes over usage of the CLI and Python clients that are used to flash and ping devices on the CAN bus.

## CLI

```javascript
btldr - CAN software updater client

Usage: btldr [options] <command> [args]

Options:
    -h  (display this text and exit)
    -v  (be verbose)

Commands:
  flash <node_id> <binary>
  ping [-a|<node_id>]
```

To flash an ECU, you'll need the binary and the ECU ID. The binary should be generated using Bazel, which will add the proper image header metadata:

```javascript
$ bazel build --config=16m1 //path/to/binary:target
```

This will generate a binary in `bazel-bin/path/to/binary/target.bin`. To flash a board with ID `0x12`, you can run

```javascript
$ btldr -v flash 0x12 ./bazel-bin/path/to/binary/target.bin
```

The client will add the flash timestamp to the image header, separate the binary into chunks, and send each chunk over CAN to the target device, which will save the data.

Once the bootloader is integrated into the Bazel monorepo, you will be able to run:

```javascript
$ bazel run //projects/btldr/client -- -v 0x12 ./bazel-bin/path/to/binary/target.bin
TODO: the path to the binary might be different... not sure.
```

## Python

A python client will be added in the future to allow for something like:

```javascript
import Client from btldr_python

client = Client()

client.flash(ECU_ID, "path/to/binary.bin", async=False)
```

# Extensions and Next Steps

## Security

Currently, the only security implementations are CRC checking and image magic, neither of which are very secure. Although it is not necessary for our team because we are not producing this software for consumers, it would be a fun project to implement an secure firmware update using self-hosted certificate authority and signing the binaries using elliptic-curve cryptography (ECDSA). The ATMega16m1 might not be powerful enough to support ECC, but other devices could or there are SPI/I2C/UART-enabled ECC chips that could handle processing for us. See [this article](https://interrupt.memfault.com/blog/secure-firmware-updates-with-code-signing) for more information.

## Extensibility

The approach taken by the [CVRA CAN Bootloader](https://github.com/cvra/can-bootloader/tree/master/client) is to group bootloader commands into datagrams, which are combinations of standard CAN frames. So a command would consist of multiple CAN frames, but a single datagram. The datagram consists of 1 frame of a bootloader version with 1 byte, 1 frame with a command ID, and any number of frames for the data. You can find details about the protocol [here](https://github.com/cvra/can-bootloader/blob/master/PROTOCOL.markdown). This approach could allow us a more extensible bootloader, but would require more processing power on the side of the ECU because we would need to buffer CAN messages and then process them once the whole dataframe arrives, making things more complicated.

## Rigid architecture and self-updating updater

# Extra learning resources

* [Device Firmware Update Architecture](https://interrupt.memfault.com/blog/device-firmware-update-cookbook) - Inspiration for the design and architecture of the system

# TODO

* Need a way to "stamp" the image as valid, either using EEPROM or by writing the image header last.

  \


