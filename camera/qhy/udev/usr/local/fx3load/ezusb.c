/*
 * Copyright (c) 2001 Stephen Williams (steve@icarus.com)
 * Copyright (c) 2001-2002 David Brownell (dbrownell@users.sourceforge.net)
 * Copyright (c) 2008 Roger Williams (rawqux@users.sourceforge.net)
 * Copyright (c) 2012 Steve Magnani (steve@digidescorp.com)
 *
 *    This source code is free software; you can redistribute it
 *    and/or modify it in source code form under the terms of the GNU
 *    General Public License as published by the Free Software
 *    Foundation; either version 2 of the License, or (at your option)
 *    any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU General Public License for more details.
 *
 *    You should have received a copy of the GNU General Public License
 *    along with this program; if not, write to the Free Software
 *    Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA
 */
#ident "$Id: ezusb.c,v 1.12 2008/10/13 21:25:29 dbrownell Exp $"

# include  <stdio.h>
# include  <errno.h>
# include  <fcntl.h>
# include  <assert.h>
# include  <limits.h>
# include  <stdint.h>
# include  <stdlib.h>
# include  <string.h>
# include  <unistd.h>

# include  <sys/ioctl.h>

# include  <linux/version.h>
# include  <linux/usb/ch9.h>
# include  <linux/usbdevice_fs.h>

#ifndef _BSD_SOURCE
#define _BSD_SOURCE
#endif
#include <endian.h>

# include "ezusb.h"

extern void logerror(const char *format, ...)
    __attribute__ ((format (printf, 1, 2)));

/*
 * This file contains functions for downloading firmware into Cypress
 * EZ-USB microcontrollers. These chips use control endpoint 0 and vendor
 * specific commands to support writing into the on-chip SRAM. They also
 * support writing into the CPUCS register, which is how we reset the
 * processor after loading firmware (including the reset vector).
 *
 * A second stage loader must be used when writing to off-chip memory,
 * or when downloading firmare into the bootstrap I2C EEPROM which may
 * be available in some hardware configurations.
 *
 * These Cypress devices are 8-bit 8051 based microcontrollers with
 * special support for USB I/O.  They come in several packages, and
 * some can be set up with external memory when device costs allow.
 * Note that the design was originally by AnchorChips, so you may find
 * references to that vendor (which was later merged into Cypress).
 * The Cypress FX parts are largely compatible with the Anchorhip ones.
 */

int verbose;

/*
 * return true iff [addr,addr+len) includes external RAM
 * for Anchorchips EZ-USB or Cypress EZ-USB FX
 */
static int fx_is_external (unsigned int addr, size_t len)
{
    /* with 8KB RAM, 0x0000-0x1b3f can be written
     * we can't tell if it's a 4KB device here
     */
    if (addr <= 0x1b3f)
	return ((addr + len) > 0x1b40);

    /* there may be more RAM; unclear if we can write it.
     * some bulk buffers may be unused, 0x1b3f-0x1f3f
     * firmware can set ISODISAB for 2KB at 0x2000-0x27ff
     */
    return 1;
}

/*
 * return true iff [addr,addr+len) includes external RAM
 * for Cypress EZ-USB FX2
 */
static int fx2_is_external (unsigned int addr, size_t len)
{
    /* 1st 8KB for data/code, 0x0000-0x1fff */
    if (addr <= 0x1fff)
	return ((addr + len) > 0x2000);

    /* and 512 for data, 0xe000-0xe1ff */
    else if (addr >= 0xe000 && addr <= 0xe1ff)
	return ((addr + len) > 0xe200);

    /* otherwise, it's certainly external */
    else
	return 1;
}

/*
 * return true iff [addr,addr+len) includes external RAM
 * for Cypress EZ-USB FX2LP
 */
static int fx2lp_is_external (unsigned int addr, size_t len)
{
    /* 1st 16KB for data/code, 0x0000-0x3fff */
    if (addr <= 0x3fff)
	return ((addr + len) > 0x4000);

    /* and 512 for data, 0xe000-0xe1ff */
    else if (addr >= 0xe000 && addr <= 0xe1ff)
	return ((addr + len) > 0xe200);

    /* otherwise, it's certainly external */
    else
	return 1;
}

/*****************************************************************************/
/*
 * Read num_bytes from fd into buf.
 * Report any errors.
 */
int read_fd(int fd, void *buf, size_t num_bytes)
{
    ssize_t bytes_read = read(fd, buf, num_bytes);

    if (bytes_read != num_bytes) {
	if (bytes_read < 0)
	    logerror("Error reading file: %s\n", strerror(errno));
	else
	    logerror("Truncated file\n");
    }

    return (bytes_read == num_bytes);
}

/*****************************************************************************/

#if LINUX_VERSION_CODE < KERNEL_VERSION(2,5,3)
/*
 * in 2.5, "struct usbdevfs_ctrltransfer" fields were renamed
 * to match the USB spec
 */
#	define bRequestType	requesttype
#	define bRequest		request
#	define wValue		value
#	define wIndex		index
#	define wLength		length
#endif

/*
 * Issue a control request to the specified device.
 * This is O/S specific ...
 */
static inline int ctrl_msg (
    int					device,
    unsigned char			requestType,
    unsigned char			request,
    unsigned short			value,
    unsigned short			index,
    unsigned char			*data,
    size_t				length
) {
    struct usbdevfs_ctrltransfer	ctrl;

    if (length > USHRT_MAX) {
	logerror("length too big\n");
	return -EINVAL;
    }

    /* 8 bytes SETUP */
    ctrl.bRequestType = requestType;
    ctrl.bRequest = request;
    ctrl.wValue   = value;
    ctrl.wLength  = (unsigned short) length;
    ctrl.wIndex = index;

    /* "length" bytes DATA */
    ctrl.data = data;

    ctrl.timeout = 10000;

    return ioctl (device, USBDEVFS_CONTROL, &ctrl);
}


/*
 * These are the requests (bRequest) that the bootstrap loader is expected
 * to recognize.  The codes are reserved by Cypress, and these values match
 * what EZ-USB hardware, or "Vend_Ax" firmware (2nd stage loader) uses.
 * Cypress' "a3load" is nice because it supports both FX and FX2, although
 * it doesn't have the EEPROM support (subset of "Vend_Ax").
 */
#define RW_INTERNAL	0xA0		/* hardware implements this one */
#define RW_EEPROM	0xA2
#define RW_MEMORY	0xA3
#define GET_EEPROM_SIZE	0xA5


/*
 * Issues the specified vendor-specific read request.
 */
static int ezusb_read (
    int					device,
    char				*label,
    unsigned char			opcode,
    unsigned short			addr,
    unsigned char			*data,
    size_t				len
) {
    int					status;

    if (verbose)
	logerror("%s, addr 0x%04x len %4zd (0x%04zx)\n", label, addr, len, len);
    status = ctrl_msg (device,
	USB_DIR_IN | USB_TYPE_VENDOR | USB_RECIP_DEVICE, opcode,
	addr, 0,
	data, len);
    if (status != len) {
	if (status < 0)
	    logerror("%s: %s\n", label, strerror(errno));
	else
	    logerror("%s ==> %d\n", label, status);
    }
    return status;
}

/*
 * Issues the specified vendor-specific write request.
 */
static int ezusb_write (
    int					device,
    char				*label,
    unsigned char			opcode,
    unsigned int			addr,
    const unsigned char			*data,
    size_t				len
) {
    int					status;

    if (verbose)
	logerror("%s, addr 0x%05x len %4zd (0x%04zx)\n", label, addr, len, len);
    status = ctrl_msg (device,
	USB_DIR_OUT | USB_TYPE_VENDOR | USB_RECIP_DEVICE, opcode,
	addr & 0xFFFF, addr >> 16,
	(unsigned char *) data, len);
    if (status != len) {
	if (status < 0)
	    logerror("%s: %s\n", label, strerror(errno));
	else
	    logerror("%s ==> %d\n", label, status);
    }
    return status;
}

/*
 * Modifies the CPUCS register to stop or reset the CPU.
 * Returns false on error.
 */
static int ezusb_cpucs (
    int			device,
    unsigned short	addr,
    int			doRun
) {
    int			status;
    unsigned char	data = doRun ? 0 : 1;

    if (verbose)
	logerror("%s\n", data ? "stop CPU" : "reset CPU");
    status = ctrl_msg (device,
	USB_DIR_OUT | USB_TYPE_VENDOR | USB_RECIP_DEVICE,
	RW_INTERNAL,
	addr, 0,
	&data, 1);
    if (status != 1) {
	char *mesg = "can't modify CPUCS";
	if (status < 0)
	    logerror("%s: %s\n", mesg, strerror(errno));
	else
	    logerror("%s\n", mesg);
	return 0;
    } else
	return 1;
}

/*
 * Returns the size of the EEPROM (assuming one is present).
 * *data == 0 means it uses 8 bit addresses (or there is no EEPROM),
 * *data == 1 means it uses 16 bit addresses
 */
static inline int ezusb_get_eeprom_type (int fd, unsigned char *data)
{
    return ezusb_read (fd, "get EEPROM size", GET_EEPROM_SIZE, 0, data, 1);
}

/*****************************************************************************/

/*
 * Parse an Intel HEX image file and invoke the poke() function on the
 * various segments to implement policies such as writing to RAM (with
 * a one or two stage loader setup, depending on the firmware) or to
 * EEPROM (two stages required).
 *
 * image	- the hex image file
 * context	- for use by poke()
 * is_external	- if non-null, used to check which segments go into
 *		  external memory (writable only by software loader)
 * poke		- called with each memory segment; errors indicated
 *		  by returning negative values.
 *
 * Caller is responsible for halting CPU as needed, such as when
 * overwriting a second stage loader.
 */
int parse_ihex (
    FILE	*image,
    void	*context,
    int		(*is_external)(unsigned int addr, size_t len),
    int		(*poke) (void *context, unsigned int addr, int external,
		      const unsigned char *data, size_t len)
)
{
    unsigned char	data [1023];
    unsigned short	data_addr = 0;
    size_t		data_len = 0;
    int			rc;
    int			first_line = 1;
    int			external = 0;

    /* Read the input file as an IHEX file, and report the memory segments
     * as we go.  Each line holds a max of 16 bytes, but downloading is
     * faster (and EEPROM space smaller) if we merge those lines into larger
     * chunks.  Most hex files keep memory segments together, which makes
     * such merging all but free.  (But it may still be worth sorting the
     * hex files to make up for undesirable behavior from tools.)
     *
     * Note that EEPROM segments max out at 1023 bytes; the download protocol
     * allows segments of up to 64 KBytes (more than a loader could handle).
     */
    for (;;) {
	char		buf [512], *cp;
	char		tmp, type;
	size_t		len;
	unsigned	idx, off;

	cp = fgets(buf, sizeof buf, image);
	if (cp == 0) {
	    logerror("EOF without EOF record!\n");
	    break;
	}

	/* EXTENSION: "# comment-till-end-of-line", for copyrights etc */
	if (buf[0] == '#')
	    continue;

	if (buf[0] != ':') {
	    logerror("not an ihex record: %s", buf);
	    return -2;
	}

	/* ignore any newline */
	cp = strchr (buf, '\n');
	if (cp)
	    *cp = 0;

	if (verbose >= 3)
	    logerror("** LINE: %s\n", buf);

	/* Read the length field (up to 16 bytes) */
	tmp = buf[3];
	buf[3] = 0;
	len = strtoul(buf+1, 0, 16);
	buf[3] = tmp;

	/* Read the target offset (address up to 64KB) */
	tmp = buf[7];
	buf[7] = 0;
	off = strtoul(buf+3, 0, 16);
	buf[7] = tmp;

	/* Initialize data_addr */
	if (first_line) {
	    data_addr = off;
	    first_line = 0;
	}

	/* Read the record type */
	tmp = buf[9];
	buf[9] = 0;
	type = strtoul(buf+7, 0, 16);
	buf[9] = tmp;

	/* If this is an EOF record, then make it so. */
	if (type == 1) {
	    if (verbose >= 2)
		logerror("EOF on hexfile\n");
	    break;
	}

	if (type != 0) {
	    logerror("unsupported record type: %u\n", type);
	    return -3;
	}

	if ((len * 2) + 11 > strlen(buf)) {
	    logerror("record too short?\n");
	    return -4;
	}

	// FIXME check for _physically_ contiguous not just virtually
	// e.g. on FX2 0x1f00-0x2100 includes both on-chip and external
	// memory so it's not really contiguous

	/* flush the saved data if it's not contiguous,
	 * or when we've buffered as much as we can.
	 */
	if (data_len != 0
		    && (off != (data_addr + data_len)
			// || !merge
			|| (data_len + len) > sizeof data)) {
	    if (is_external)
		external = is_external (data_addr, data_len);
	    rc = poke (context, data_addr, external, data, data_len);
	    if (rc < 0)
		return -1;
	    data_addr = off;
	    data_len = 0;
	}

	/* append to saved data, flush later */
	for (idx = 0, cp = buf+9 ;  idx < len ;  idx += 1, cp += 2) {
	    tmp = cp[2];
	    cp[2] = 0;
	    data [data_len + idx] = strtoul(cp, 0, 16);
	    cp[2] = tmp;
	}
	data_len += len;
    }


    /* flush any data remaining */
    if (data_len != 0) {
	if (is_external)
	    external = is_external (data_addr, data_len);
	rc = poke (context, data_addr, external, data, data_len);
	if (rc < 0)
	    return -1;
    }
    return 0;
}

/*
 * Parse a FX3 '.img' file and invoke the poke() function on the
 * various segments to implement policies such as writing to RAM (with
 * a one or two stage loader setup, depending on the firmware) or to
 * EEPROM (two stages required).
 *
 * img_fd	- the image file
 * context	- for use by poke()
 * poke		- called with each memory segment; errors indicated
 *		  by returning negative values.
 *
 * Caller is responsible for halting CPU as needed, such as when
 * overwriting a second stage loader.
 */
int parse_img (
    int		img_fd,
    void	*context,
    int 	(*poke) (void *context, unsigned int addr, int external,
		      const unsigned char *data, size_t len)
)
{
    unsigned char	header[4];
    unsigned char	data[4096];
    int			rc = -1;

    /* Validate the header */
    if (!read_fd(img_fd, header, sizeof(header)))
	return -1;

    if ((header[0] != 'C') || (header[1] != 'Y')) {
	logerror("Invalid file: missing CYpress signature\n");
	return -1;
    }

    if (header[3] != 0xB0) {
	logerror("Invalid file: format 0x%02X, expected 0xB0\n", header[3]);
	return -1;
    }

    /* Now process data segments */
    do {
	uint32_t  segment_addr, cur_addr;
	uint32_t  segment_len, bytes_remaining, bytes_this_chunk;

	rc = -1;	/* In case of error */
	if (!read_fd(img_fd, &segment_len, sizeof(segment_len)))
	    break;

	if (!read_fd(img_fd, &segment_addr, sizeof(segment_addr)))
	    break;

	segment_len  = le32toh(segment_len) << 2;
	segment_addr = le32toh(segment_addr);

	cur_addr        = segment_addr;
	bytes_remaining = segment_len;

	/* Make sure we poke() if segment_len == 0,
	 * as FX3 interprets this as a "run from address" command
	 */

	do {
	    bytes_this_chunk = bytes_remaining;
	    if (bytes_this_chunk > sizeof(data))
		bytes_this_chunk = sizeof(data);

	    if (bytes_this_chunk && !read_fd(img_fd, data, bytes_this_chunk)) {
		rc = -1;
		break;
	    }

	    rc = poke (context, cur_addr, 0, data, bytes_this_chunk);

	    cur_addr        += bytes_this_chunk;
	    bytes_remaining -= bytes_this_chunk;
	} while ((rc == 0) && (bytes_remaining > 0));

	if (segment_len == 0)
	    break;

    } while (rc == 0);

    return rc;
}

/*****************************************************************************/

/*
 * For writing to RAM using a first (hardware) or second (software)
 * stage loader and 0xA0 or 0xA3 vendor requests
 */
typedef enum {
    _undef = 0,
    internal_only,		/* hardware first-stage loader */
    skip_internal,		/* first phase, second-stage loader */
    skip_external		/* second phase, second-stage loader */
} ram_mode;

struct ram_poke_context {
    int		device;
    ram_mode	mode;
    unsigned	total, count;
};

# define RETRY_LIMIT 5

static int ram_poke (
    void		*context,
    unsigned int	addr,
    int			external,
    const unsigned char	*data,
    size_t		len
) {
    struct ram_poke_context	*ctx = context;
    int			rc;
    unsigned		retry = 0;

    switch (ctx->mode) {
    case internal_only:		/* CPU should be stopped */
	if (external) {
	    logerror("can't write %zd bytes external memory at 0x%05x\n",
		len, addr);
	    return -EINVAL;
	}
	break;
    case skip_internal:		/* CPU must be running */
	if (!external) {
	    if (verbose >= 2) {
		logerror("SKIP on-chip RAM, %zd bytes at 0x%05x\n",
		    len, addr);
	    }
	    return 0;
	}
	break;
    case skip_external:		/* CPU should be stopped */
	if (external) {
	    if (verbose >= 2) {
		logerror("SKIP external RAM, %zd bytes at 0x%05x\n",
		    len, addr);
	    }
	    return 0;
	}
	break;
    default:
	logerror("bug\n");
	return -EDOM;
    }

    ctx->total += len;
    ctx->count++;

    /* Retry this till we get a real error. Control messages are not
     * NAKed (just dropped) so time out means is a real problem.
     */
    while ((rc = ezusb_write (ctx->device,
		    external ? "write external" : "write on-chip",
		    external ? RW_MEMORY : RW_INTERNAL,
		    addr, data, len)) < 0
		&& retry < RETRY_LIMIT) {
	  if (errno != ETIMEDOUT)
		break;
	  retry += 1;
    }
    return (rc < 0) ? -errno : 0;
}

/*
 * Load a FX3 'img' file into target RAM. The dev_fd is the open "usbfs"
 * device, and the path is the name of the source file. Open the file,
 * parse the bytes, and write them in one or two phases.
 *
 * This uses the first stage loader, built into FX3 hardware but limited
 * to writing on-chip memory.  Everything is written during one stage.
 */
static int fx3_load_ram (int dev_fd, const char *path, int stage)
{
    int				image_fd;
    struct ram_poke_context	ctx;
    int				status;

    if (stage != 0) {
	logerror("Two-stage load not yet supported for FX3\n");
	return -1;
    }

    image_fd = open(path, O_RDONLY);
    if (image_fd < 0) {
	logerror("%s: unable to open for input.\n", path);
	return -2;
    } else if (verbose)
	logerror("open RAM image %s\n", path);

    ctx.device = dev_fd;
    ctx.total  = 0;
    ctx.count  = 0;
    ctx.mode   = internal_only;

    status = parse_img(image_fd, &ctx, ram_poke);
    if (status < 0) {
	logerror("unable to download %s\n", path);
	return status;
    }

    if (verbose) {
	logerror("... WROTE: %d bytes, %d segments, avg %d\n",
	    ctx.total, ctx.count, ctx.total / ctx.count);
    }

    return 0;
}

/*
 * Load an Intel HEX file into target RAM. The fd is the open "usbfs"
 * device, and the path is the name of the source file. Open the file,
 * parse the bytes, and write them in one or two phases.
 *
 * If stage == 0, this uses the first stage loader, built into EZ-USB
 * hardware but limited to writing on-chip memory or CPUCS.  Everything
 * is written during one stage, unless there's an error such as the image
 * holding data that needs to be written to external memory.
 *
 * Otherwise, things are written in two stages.  First the external
 * memory is written, expecting a second stage loader to have already
 * been loaded.  Then file is re-parsed and on-chip memory is written.
 */
int ezusb_load_ram (int fd, const char *path, const char *type, int stage)
{
    FILE			*image;
    unsigned short		cpucs_addr;
    int				(*is_external)(unsigned int off, size_t len);
    struct ram_poke_context	ctx;
    int				status;

    /* FX3 loading differs significantly from that of previous devices */
    if (strcmp(type, "fx3") == 0)
	return fx3_load_ram (fd, path, stage);


    image = fopen (path, "r");
    if (image == 0) {
	logerror("%s: unable to open for input.\n", path);
	return -2;
    } else if (verbose)
	logerror("open RAM hexfile image %s\n", path);

    /* EZ-USB original/FX and FX2 devices differ, apart from the 8051 core */
    if (strcmp(type, "fx2lp") == 0) {
	cpucs_addr = 0xe600;
	is_external = fx2lp_is_external;
    } else if (strcmp(type, "fx2") == 0) {
	cpucs_addr = 0xe600;
	is_external = fx2_is_external;
    } else {
	cpucs_addr = 0x7f92;
	is_external = fx_is_external;
    }

    /* use only first stage loader? */
    if (!stage) {
	ctx.mode = internal_only;

	/* don't let CPU run while we overwrite its code/data */
	if (!ezusb_cpucs (fd, cpucs_addr, 0))
	    return -1;

    /* 2nd stage, first part? loader was already downloaded */
    } else {
	ctx.mode = skip_internal;

	/* let CPU run; overwrite the 2nd stage loader later */
	if (verbose)
	    logerror("2nd stage:  write external memory\n");
    }

    /* scan the image, first (maybe only) time */
    ctx.device = fd;
    ctx.total = ctx.count = 0;
    status = parse_ihex (image, &ctx, is_external, ram_poke);
    if (status < 0) {
	logerror("unable to download %s\n", path);
	return status;
    }

    /* second part of 2nd stage: rescan */
    if (stage) {
	ctx.mode = skip_external;

	/* don't let CPU run while we overwrite the 1st stage loader */
	if (!ezusb_cpucs (fd, cpucs_addr, 0))
	    return -1;

	/* at least write the interrupt vectors (at 0x0000) for reset! */
	rewind (image);
	if (verbose)
	    logerror("2nd stage:  write on-chip memory\n");
	status = parse_ihex (image, &ctx, is_external, ram_poke);
	if (status < 0) {
	    logerror("unable to completely download %s\n", path);
	    return status;
	}
    }

    if (verbose)
	logerror("... WROTE: %d bytes, %d segments, avg %d\n",
	    ctx.total, ctx.count, ctx.total / ctx.count);

    /* now reset the CPU so it runs what we just downloaded */
    if (!ezusb_cpucs (fd, cpucs_addr, 1))
	return -1;

    return 0;
}

/*****************************************************************************/

/*
 * For writing to EEPROM using a 2nd stage loader
 */
struct eeprom_poke_context {
    int			device;
    unsigned short	ee_addr;	/* next free address */
    int			last;
};

static int eeprom_poke (
    void		*context,
    unsigned int	addr,
    int			external,
    const unsigned char	*data,
    size_t		len
) {
    struct eeprom_poke_context	*ctx = context;
    int			rc;
    unsigned char	header [4];

    if (external) {
      logerror(
	    "EEPROM can't init %zd bytes external memory at 0x%05x\n",
	    len, addr);
	return -EINVAL;
    }

    if (len > 1023) {
	logerror("not fragmenting %zd bytes\n", len);
	return -EDOM;
    }

    /* NOTE:  No retries here.  They don't seem to be needed;
     * could be added if that changes.
     */

    /* write header */
    header [0] = len >> 8;
    header [1] = len;
    header [2] = addr >> 8;
    header [3] = addr;
    if (ctx->last)
	header [0] |= 0x80;
    if ((rc = ezusb_write (ctx->device, "write EEPROM segment header",
		    RW_EEPROM,
		    ctx->ee_addr, header, 4)) < 0)
	return rc;

    /* write code/data */
    if ((rc = ezusb_write (ctx->device, "write EEPROM segment",
		    RW_EEPROM,
		    ctx->ee_addr + 4, data, len)) < 0)
	return rc;

    /* next shouldn't overwrite it */
    ctx->ee_addr += 4 + len;

    return 0;
}

/*
 * Load an Intel HEX file into target (large) EEPROM, set up to boot from
 * that EEPROM using the specified microcontroller-specific config byte.
 * (Defaults:  FX2 0x08, FX 0x00, AN21xx n/a)
 *
 * Caller must have pre-loaded a second stage loader that knows how
 * to handle the EEPROM write requests.
 */
int ezusb_load_eeprom (int dev, const char *path, const char *type, int config)
{
    FILE			*image;
    unsigned short		cpucs_addr;
    int				(*is_external)(unsigned int off, size_t len);
    struct eeprom_poke_context	ctx;
    int				status;
    unsigned char		value, first_byte;

    if (strcmp ("fx3", type) == 0) {
	logerror("FX3 EEPROM loading is not yet supported.\n");
	return -1;
    }

    if (ezusb_get_eeprom_type (dev, &value) != 1 || value != 1) {
	logerror("don't see a large enough EEPROM\n");
	return -1;
    }

    image = fopen (path, "r");
    if (image == 0) {
	logerror("%s: unable to open for input.\n", path);
	return -2;
    } else if (verbose)
	logerror("open EEPROM hexfile image %s\n", path);

    if (verbose)
	logerror("2nd stage:  write boot EEPROM\n");

    /* EZ-USB family devices differ, apart from the 8051 core */
    if (strcmp ("fx2", type) == 0) {
	first_byte = 0xC2;
	cpucs_addr = 0xe600;
	is_external = fx2_is_external;
	ctx.ee_addr = 8;
	config &= 0x4f;
	logerror(
	    "FX2:  config = 0x%02x, %sconnected, I2C = %d KHz\n",
	    config,
	    (config & 0x40) ? "dis" : "",
		// NOTE:  old chiprevs let CPU clock speed be set
		// or cycle inverted here.  You shouldn't use those.
		// (Silicon revs B, C?  Rev E is nice!)
	    (config & 0x01) ? 400 : 100
	    );

    } else if (strcmp ("fx2lp", type) == 0) {
	first_byte = 0xC2;
	cpucs_addr = 0xe600;
	is_external = fx2lp_is_external;
	ctx.ee_addr = 8;
	config &= 0x4f;
	logerror (
	    "FX2LP:  config = 0x%02x, %sconnected, I2C = %d KHz\n",
	    config,
	    (config & 0x40) ? "dis" : "",
	    (config & 0x01) ? 400 : 100
	    );
    } else if (strcmp ("fx", type) == 0) {
	first_byte = 0xB6;
	cpucs_addr = 0x7f92;
	is_external = fx_is_external;
	ctx.ee_addr = 9;
	config &= 0x07;
	logerror(
	    "FX:  config = 0x%02x, %d MHz%s, I2C = %d KHz\n",
	    config,
	    ((config & 0x04) ? 48 : 24),
	    (config & 0x02) ? " inverted" : "",
	    (config & 0x01) ? 400 : 100
	    );

    } else if (strcmp ("an21", type) == 0) {
	first_byte = 0xB2;
	cpucs_addr = 0x7f92;
	is_external = fx_is_external;
	ctx.ee_addr = 7;
	config = 0;
	logerror("AN21xx:  no EEPROM config byte\n");

    } else {
	logerror("?? Unrecognized microcontroller type %s ??\n", type);
	return -1;
    }

    /* make sure the EEPROM won't be used for booting,
     * in case of problems writing it
     */
    value = 0x00;
    status = ezusb_write (dev, "mark EEPROM as unbootable",
	    RW_EEPROM, 0, &value, sizeof value);
    if (status < 0)
	return status;

    /* scan the image, write to EEPROM */
    ctx.device = dev;
    ctx.last = 0;
    status = parse_ihex (image, &ctx, is_external, eeprom_poke);
    if (status < 0) {
	logerror("unable to write EEPROM %s\n", path);
	return status;
    }

    /* append a reset command */
    value = 0;
    ctx.last = 1;
    status = eeprom_poke (&ctx, cpucs_addr, 0, &value, sizeof value);
    if (status < 0) {
	logerror("unable to append reset to EEPROM %s\n", path);
	return status;
    }

    /* write the config byte for FX, FX2 */
    if (strcmp ("an21", type) != 0) {
	value = config;
	status = ezusb_write (dev, "write config byte",
		RW_EEPROM, 7, &value, sizeof value);
	if (status < 0)
	    return status;
    }

    /* EZ-USB FX has a reserved byte */
    if (strcmp ("fx", type) == 0) {
	value = 0;
	status = ezusb_write (dev, "write reserved byte",
		RW_EEPROM, 8, &value, sizeof value);
	if (status < 0)
	    return status;
    }

    /* make the EEPROM say to boot from this EEPROM */
    status = ezusb_write (dev, "write EEPROM type byte",
	    RW_EEPROM, 0, &first_byte, sizeof first_byte);
    if (status < 0)
	return status;

    /* Note:  VID/PID/version aren't written.  They should be
     * written if the EEPROM type is modified (to B4 or C0).
     */

    return 0;
}

/*
 * $Log: ezusb.c,v $
 * Revision 1.12  2008/10/13 21:25:29  dbrownell
 * Whitespace fixes.
 *
 * Revision 1.11  2008/10/13 21:23:23  dbrownell
 * From Roger Williams <roger@qux.com>:  FX2LP support
 *
 * Revision 1.10  2008/10/13 21:22:10  dbrownell
 * Built against current kernel headers; remove various warnings.
 *
 * Revision 1.9  2005/01/11 03:58:02  dbrownell
 * From Dirk Jagdmann <doj@cubic.org>:  optionally output messages to
 * syslog instead of stderr.
 *
 * Revision 1.8  2005/01/11 03:08:12  dbrownell
 * Patch from Giovanni Mels, so the string is always null terminated
 * rather than only with "verbose >= 3" ... and the length test is
 * changed accordingly.
 *
 * Revision 1.7  2002/04/12 00:25:58  dbrownell
 * - support older AnchorChips style EEPROMs too
 * - minor bugfix for config byte mask in FX
 *
 * Revision 1.6  2002/04/02 08:34:16  dbrownell
 * minor stuff:
 * - don't assume last segment in file is always internal
 * - tweak diagnostics for easier matchup to 8051 linker maps
 * - minor comment/format updates
 *
 * Revision 1.5  2002/02/26 20:06:31  dbrownell
 * - Rewrite for 2nd stage loader support, so this can write
 *   to external RAM and (given the right loader) EEPROM.
 * - Handle usbfs API changes in Linux kernel 2.5.
 * - A "more verbose" option.
 *
 * Revision 1.4  2002/01/17 14:47:44  dbrownell
 * init first line, remove warnings
 *
 * Revision 1.3  2001/12/27 17:59:33  dbrownell
 * merge adjacent hex records, and optionally show writes
 *
 * Revision 1.2  2001/12/14 11:24:04  dbrownell
 * Add sanity check: reject requests to load off-chip memory,
 * The EZ-USB devices just fail silently in these cases.
 *
 * Revision 1.1  2001/06/12 00:00:50  stevewilliams
 *  Added the fxload program.
 *  Rework root makefile and hotplug.spec to install in prefix
 *  location without need of spec file for install.
 *
 */

