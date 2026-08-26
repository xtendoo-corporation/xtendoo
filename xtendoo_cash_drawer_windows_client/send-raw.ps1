param(
    [string]$PrinterName,
    [string]$DocName = "RawPrintJob",
    [Parameter(Mandatory=$true)]
    [string]$HexBytes
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class RawPrinterHelper
{
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public class DOCINFO
    {
        [MarshalAs(UnmanagedType.LPWStr)]
        public string pDocName;

        [MarshalAs(UnmanagedType.LPWStr)]
        public string pOutputFile;

        [MarshalAs(UnmanagedType.LPWStr)]
        public string pDataType;
    }

    [DllImport("winspool.drv", EntryPoint="OpenPrinterW", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);

    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);

    [DllImport("winspool.drv", EntryPoint="StartDocPrinterW", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern int StartDocPrinter(IntPtr hPrinter, int Level, [In] DOCINFO pDocInfo);

    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool EndDocPrinter(IntPtr hPrinter);

    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool StartPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool EndPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool WritePrinter(IntPtr hPrinter, byte[] pBytes, int dwCount, out int dwWritten);

    public static void SendBytesToPrinter(string printerName, byte[] bytes, string docName)
    {
        IntPtr hPrinter;

        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero))
            throw new Exception("OpenPrinter failed: " + Marshal.GetLastWin32Error());

        try
        {
            DOCINFO di = new DOCINFO();
            di.pDocName = docName;
            di.pDataType = "RAW";
            di.pOutputFile = null;

            int jobId = StartDocPrinter(hPrinter, 1, di);
            if (jobId <= 0)
                throw new Exception("StartDocPrinter failed: " + Marshal.GetLastWin32Error());

            try
            {
                if (!StartPagePrinter(hPrinter))
                    throw new Exception("StartPagePrinter failed: " + Marshal.GetLastWin32Error());

                try
                {
                    int written;
                    if (!WritePrinter(hPrinter, bytes, bytes.Length, out written))
                        throw new Exception("WritePrinter failed: " + Marshal.GetLastWin32Error());

                    if (written != bytes.Length)
                        throw new Exception("No se escribieron todos los bytes. Escritos: " + written);
                }
                finally
                {
                    EndPagePrinter(hPrinter);
                }
            }
            finally
            {
                EndDocPrinter(hPrinter);
            }
        }
        finally
        {
            ClosePrinter(hPrinter);
        }
    }
}
"@

if ([string]::IsNullOrWhiteSpace($PrinterName)) {
    $defaultPrinter = Get-CimInstance Win32_Printer |
        Where-Object { $_.Default -eq $true } |
        Select-Object -First 1

    if (-not $defaultPrinter) {
        throw "No hay impresora predeterminada configurada en Windows"
    }

    $PrinterName = $defaultPrinter.Name
}

$byteList = $HexBytes.Split(',') | ForEach-Object {
    [Convert]::ToByte($_.Trim(), 16)
}

[RawPrinterHelper]::SendBytesToPrinter($PrinterName, $byteList, $DocName)

$result = @{
    printer   = $PrinterName
    bytesSent = $byteList.Length
}

$result | ConvertTo-Json -Compress