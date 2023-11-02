#include <fitsio.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include "qhyccd.h"
#include <ctime>
#include <cstdlib>
#include <cstdlib>

int main(int argc, char *argv[])
{
	if (argc != 6) {
		printf("Call like this:\n./singleFrameMode 10 10 140 2000 1\n- USB Trafic\n- Gain\n- Offset\n- Exposure\n- Bin\n");
		return 1;
	}

	int USB_TRAFFIC = atoi(argv[1]); // 10
	int CHIP_GAIN = atoi(argv[2]); // 10
	int CHIP_OFFSET = atoi(argv[3]); // 140
	int EXPOSURE_TIME = atoi(argv[4]); // 2000
	double EXPOSURE_TIME_DOUBLE; // for writing into fits header
	int camBinX = atoi(argv[5]); // 1
	int camBinY = atoi(argv[5]); // 1

	printf("Try to capture with trafic=%d, offset=%d, gain=%d, exp=%d, bin=%d\n", USB_TRAFFIC, CHIP_OFFSET, CHIP_GAIN, EXPOSURE_TIME, camBinX);

	double chipWidthMM;
	double chipHeightMM;
	double pixelWidthUM;
	double pixelHeightUM;

	unsigned int roiStartX;
	unsigned int roiStartY;
	unsigned int roiSizeX;
	unsigned int roiSizeY;

	unsigned int overscanStartX;
	unsigned int overscanStartY;
	unsigned int overscanSizeX;
	unsigned int overscanSizeY;

	unsigned int effectiveStartX;
	unsigned int effectiveStartY;
	unsigned int effectiveSizeX;
	unsigned int effectiveSizeY;

	unsigned int maxImageSizeX;
	unsigned int maxImageSizeY;
	unsigned int bpp;
	unsigned int channels;

	unsigned char *pImgData = 0;

	// init SDK
	unsigned int retVal = InitQHYCCDResource();
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("SDK resources initialized.\n");
	}
	else
	{
		printf("Cannot initialize SDK resources, error: %d\n", retVal);
		return 1;
	}

	EnableQHYCCDMessage(false);

	// scan cameras
	int camCount = ScanQHYCCD();
	if (camCount > 0)
	{
		printf("Number of QHYCCD cameras found: %d \n", camCount);
	}
	else
	{
		printf("No QHYCCD camera found, please check USB or power.\n");
		return 1;
	}

	// iterate over all attached cameras
	bool camFound = false;
	char camId[32];

	for (int i = 0; i < camCount; i++)
	{
		retVal = GetQHYCCDId(i, camId);
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("Application connected to the following camera from the list: Index: %d,  cameraID = %s\n", (i + 1), camId);
			camFound = true;
			break;
		}
	}

	if (!camFound)
	{
		printf("The detected camera is not QHYCCD or other error.\n");
		// release sdk resources
		retVal = ReleaseQHYCCDResource();
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("SDK resources released.\n");
		}
		else
		{
			printf("Cannot release SDK resources, error %d.\n", retVal);
		}
		return 1;
	}

	// open camera
	qhyccd_handle *pCamHandle = OpenQHYCCD(camId);
	if (pCamHandle != NULL)
	{
		printf("Open QHYCCD success.\n");
	}
	else
	{
		printf("Open QHYCCD failure.\n");
		return 1;
	}

	// check camera support single frame
	retVal = IsQHYCCDControlAvailable(pCamHandle, CAM_SINGLEFRAMEMODE);
	if (QHYCCD_ERROR == retVal)
	{
		printf("The detected camera is not support single frame.\n");
		// release sdk resources
		retVal = ReleaseQHYCCDResource();
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("SDK resources released.\n");
		}
		else
		{
			printf("Cannot release SDK resources, error %d.\n", retVal);
		}
		return 1;
	}
	
	// set single frame mode
	int mode = 0;
	retVal = SetQHYCCDStreamMode(pCamHandle, mode);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("SetQHYCCDStreamMode set to: %d, success.\n", mode);
	}
	else
	{
		printf("SetQHYCCDStreamMode: %d failure, error: %d\n", mode, retVal);
		return 1;
	}

	// initialize camera
	retVal = InitQHYCCD(pCamHandle);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("InitQHYCCD success.\n");
	}
	else
	{
		printf("InitQHYCCD faililure, error: %d\n", retVal);
		return 1;
	}

	// get overscan area
	retVal = GetQHYCCDOverScanArea(pCamHandle, &overscanStartX, &overscanStartY, &overscanSizeX, &overscanSizeY);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("GetQHYCCDOverScanArea:\n");
		printf("Overscan Area startX x startY : %d x %d\n", overscanStartX, overscanStartY);
		printf("Overscan Area sizeX  x sizeY  : %d x %d\n", overscanSizeX, overscanSizeY);
	}
	else
	{
		printf("GetQHYCCDOverScanArea failure, error: %d\n", retVal);
		return 1;
	}

	// get effective area
	retVal = GetQHYCCDOverScanArea(pCamHandle, &effectiveStartX, &effectiveStartY, &effectiveSizeX, &effectiveSizeY);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("GetQHYCCDEffectiveArea:\n");
		printf("Effective Area startX x startY: %d x %d\n", effectiveStartX, effectiveStartY);
		printf("Effective Area sizeX  x sizeY : %d x %d\n", effectiveSizeX, effectiveSizeY);
	}
	else
	{
		printf("GetQHYCCDOverScanArea failure, error: %d\n", retVal);
		return 1;
	}

	// get chip info
	retVal = GetQHYCCDChipInfo(pCamHandle, &chipWidthMM, &chipHeightMM, &maxImageSizeX, &maxImageSizeY, &pixelWidthUM, &pixelHeightUM, &bpp);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("GetQHYCCDChipInfo:\n");
		printf("Effective Area startX x startY: %d x %d\n", effectiveStartX, effectiveStartY);
		printf("Chip  size width x height     : %.3f x %.3f [mm]\n", chipWidthMM, chipHeightMM);
		printf("Pixel size width x height     : %.3f x %.3f [um]\n", pixelWidthUM, pixelHeightUM);
		printf("Image size width x height     : %d x %d\n", maxImageSizeX, maxImageSizeY);
	}
	else
	{
		printf("GetQHYCCDChipInfo failure, error: %d\n", retVal);
		return 1;
	}

	// set ROI
	roiStartX = 0;
	roiStartY = 0;
	roiSizeX = maxImageSizeX;
	roiSizeY = maxImageSizeY;

	// check color camera
	retVal = IsQHYCCDControlAvailable(pCamHandle, CAM_COLOR);
	if (retVal == BAYER_GB || retVal == BAYER_GR || retVal == BAYER_BG || retVal == BAYER_RG)
	{
		printf("This is a color camera.\n");
		printf("even this is a color camera, in Single Frame mode THE SDK ONLY SUPPORT RAW OUTPUT.So please do not set SetQHYCCDDebayerOnOff() to true;");
		//SetQHYCCDDebayerOnOff(pCamHandle, true);
		//SetQHYCCDParam(pCamHandle, CONTROL_WBR, 20);
		//SetQHYCCDParam(pCamHandle, CONTROL_WBG, 20);
		//SetQHYCCDParam(pCamHandle, CONTROL_WBB, 20);
	}
	else
	{
		printf("This is a mono camera.\n");
	}

	// check traffic
	retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_USBTRAFFIC);
	if (QHYCCD_SUCCESS == retVal)
	{
		retVal = SetQHYCCDParam(pCamHandle, CONTROL_USBTRAFFIC, USB_TRAFFIC);
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("SetQHYCCDParam CONTROL_USBTRAFFIC set to: %d, success.\n", USB_TRAFFIC);
		}
		else
		{
			printf("SetQHYCCDParam CONTROL_USBTRAFFIC failure, error: %d\n", retVal);
			return 1;
		}
	}

	// check gain
	retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_GAIN);
	if (QHYCCD_SUCCESS == retVal)
	{
		retVal = SetQHYCCDParam(pCamHandle, CONTROL_GAIN, CHIP_GAIN);
		if (retVal == QHYCCD_SUCCESS)
		{
			printf("SetQHYCCDParam CONTROL_GAIN set to: %d, success\n", CHIP_GAIN);
		}
		else
		{
			printf("SetQHYCCDParam CONTROL_GAIN failure, error: %d\n", retVal);
			return 1;
		}
	}

	// check offset
	retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_OFFSET);
	if (QHYCCD_SUCCESS == retVal)
	{
		retVal = SetQHYCCDParam(pCamHandle, CONTROL_OFFSET, CHIP_OFFSET);
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("SetQHYCCDParam CONTROL_OFFSET set to: %d, success.\n", CHIP_OFFSET);
		}
		else
		{
			printf("SetQHYCCDParam CONTROL_OFFSET failed.\n");
			return 1;
		}
	}

	// set exposure time
	retVal = SetQHYCCDParam(pCamHandle, CONTROL_EXPOSURE, EXPOSURE_TIME);
	printf("SetQHYCCDParam CONTROL_EXPOSURE set to: %d, success.\n", EXPOSURE_TIME);
	if (QHYCCD_SUCCESS == retVal)
	{}
	else
	{
		printf("SetQHYCCDParam CONTROL_EXPOSURE failure, error: %d\n", retVal);
		return 1;
	}

	// set image resolution
	retVal = SetQHYCCDResolution(pCamHandle, roiStartX, roiStartY, roiSizeX, roiSizeY);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("SetQHYCCDResolution roiStartX x roiStartY: %d x %d\n", roiStartX, roiStartY);
		printf("SetQHYCCDResolution roiSizeX  x roiSizeY : %d x %d\n", roiSizeX, roiSizeY);
	}
	else
	{
		printf("SetQHYCCDResolution failure, error: %d\n", retVal);
		return 1;
	}

	// set binning mode
	retVal = SetQHYCCDBinMode(pCamHandle, camBinX, camBinY);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("SetQHYCCDBinMode set to: binX: %d, binY: %d, success.\n", camBinX, camBinY);
	}
	else
	{
		printf("SetQHYCCDBinMode failure, error: %d\n", retVal);
		return 1;
	}

	// set bit resolution
	retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_TRANSFERBIT);
	if (QHYCCD_SUCCESS == retVal)
	{
		retVal = SetQHYCCDBitsMode(pCamHandle, 16);
		if (QHYCCD_SUCCESS == retVal)
		{
			printf("SetQHYCCDParam CONTROL_GAIN set to: %d, success.\n", CONTROL_TRANSFERBIT);
		}
		else
		{
			printf("SetQHYCCDParam CONTROL_GAIN failure, error: %d\n", retVal);
			return 1;
		}
	}

	// single frame
	printf("ExpQHYCCDSingleFrame(pCamHandle) - start...\n");
	retVal = ExpQHYCCDSingleFrame(pCamHandle);
	printf("ExpQHYCCDSingleFrame(pCamHandle) - end...\n");
	if (QHYCCD_ERROR != retVal)
	{
		printf("ExpQHYCCDSingleFrame success.\n");
		if (QHYCCD_READ_DIRECTLY != retVal)
		{
			sleep(1);
		}
	}
	else
	{
		printf("ExpQHYCCDSingleFrame failure, error: %d\n", retVal);
		return 1;
	}

	// get requested memory lenght
	uint32_t length = GetQHYCCDMemLength(pCamHandle);

	if (length > 0)
	{
		pImgData = new unsigned char[length];
		memset(pImgData, 0, length);
		printf("Allocated memory for frame: %d [uchar].\n", length);
	}
	else
	{
		printf("Cannot allocate memory for frame.\n");
		return 1;
	}

	// get single frame
	retVal = GetQHYCCDSingleFrame(pCamHandle, &roiSizeX, &roiSizeY, &bpp, &channels, pImgData);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("GetQHYCCDSingleFrame: %d x %d, bpp: %d, channels: %d, success.\n", roiSizeX, roiSizeY, bpp, channels);
		// Image Processing to .fits file

		// Create File
		fitsfile *fptr;
		int status = 0;
		long naxes[2] = {roiSizeX, roiSizeY};

		const char *fitsfilename = "/fits/current.fit";

		// Remove if exists already
		remove(fitsfilename);

		// Create File
		fits_create_file(&fptr, fitsfilename, &status);
		fits_create_img(fptr, USHORT_IMG, 2, naxes, &status);

		// Headers Information
		EXPOSURE_TIME_DOUBLE = EXPOSURE_TIME / 1000000.;
		fits_update_key(fptr, TDOUBLE, "EXPTIME", &EXPOSURE_TIME_DOUBLE, "Exposure time in seconds", &status);
		fits_update_key(fptr, TINT, "OFFSET", &CHIP_OFFSET, "Offset Setting", &status);
		fits_update_key(fptr, TINT, "GAIN", &CHIP_GAIN, "Gain Setting", &status);
		fits_update_key(fptr, TINT, "XBINNING", &camBinX, "Binning Setting", &status);
		fits_update_key(fptr, TINT, "YBINNING", &camBinY, "Binning Setting", &status);

		time_t rawtime;
		struct tm * timeinfo;
		char buffer[80];
		time (&rawtime);
		timeinfo = gmtime(&rawtime);

		strftime(buffer,sizeof(buffer),"%Y-%m-%dT%H:%M:%S",timeinfo);

		fits_update_key(fptr, TSTRING, "DATE-OBS", &buffer, "Datetime image taken", &status);

		// Write to File
		fits_write_img(fptr, TUSHORT, 1, roiSizeX * roiSizeY, pImgData, &status);

		// Close File
		fits_close_file(fptr, &status);
	}
	else
	{
		printf("GetQHYCCDSingleFrame failure, error: %d\n", retVal);
	}

	delete [] pImgData;

	retVal = CancelQHYCCDExposingAndReadout(pCamHandle);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("CancelQHYCCDExposingAndReadout success.\n");
	}
	else
	{
		printf("CancelQHYCCDExposingAndReadout failure, error: %d\n", retVal);
		return 1;
	}

	// close camera handle
	retVal = CloseQHYCCD(pCamHandle);
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("Close QHYCCD success.\n");
	}
	else
	{
		printf("Close QHYCCD failure, error: %d\n", retVal);
	}

	// release sdk resources
	retVal = ReleaseQHYCCDResource();
	if (QHYCCD_SUCCESS == retVal)
	{
		printf("SDK resources released.\n");
	}
	else
	{
		printf("Cannot release SDK resources, error %d.\n", retVal);
		return 1;
	}

	return 0;
}
