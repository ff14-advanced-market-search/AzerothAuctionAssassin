using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;

namespace AzerothAuctionAssassin
{
    internal static class Program
    {
        /// <summary>
        ///  The main entry point for the application.
        /// </summary>
        [STAThread]

        static void Main()
        {



            string appversion = "1.0.4";
            string appPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AzerothAuctionAssassin");
            string currentVersionPath = Path.Combine(appPath, appversion);
            string pythonPath = Path.Combine(currentVersionPath, "python-embedded");
            string requirementsPath = $"{currentVersionPath}\\requirements.txt";
            string mainPythonFilePath = $"{currentVersionPath}\\AzerothAuctionAssassin.py";




            installApp(appPath, appversion);
            InstallPython(pythonPath);
            InstallPipe(pythonPath);
            InstallPipeRequirements(currentVersionPath,pythonPath, requirementsPath);
            RunPythonFile(currentVersionPath,pythonPath,mainPythonFilePath);
        }


        static void installApp(string installPath,string appVersion)
        {

            if (!Directory.Exists(installPath))
            {
                Directory.CreateDirectory(installPath);
            }

            string currentVersionPath = Path.Combine(installPath, appVersion);

            if (!Directory.Exists(currentVersionPath))
            {
                string zipFile_path = Path.Combine(Path.GetTempPath(), "AzerothAuctionAssassin.zip");
                File.WriteAllBytes(zipFile_path, Properties.Resources.app);
                UnzipToFolder(zipFile_path, currentVersionPath);
            }
            else
            {
                return;
            }

        }
        public static void UnzipToFolder(string zipFilePath,string folderPath)
        {
            // Ensure the zip file exists
            if (!File.Exists(zipFilePath))
            {
                throw new FileNotFoundException("The specified zip file could not be found.", zipFilePath);
            }



            // Extract the contents of the zip file to the directory
            ZipFile.ExtractToDirectory(zipFilePath, folderPath,true);

    
        }



        static void InstallPython(string pythonInstallPath)
        {


            if (!Directory.Exists(pythonInstallPath))
            {
                Directory.CreateDirectory(pythonInstallPath);
            }
            else
            {
                //embedded python is installed.
                return;
            }


            string downloadPath = Path.Combine(Path.GetTempPath(), "python.zip");
            File.WriteAllBytes(downloadPath, Properties.Resources.python_3_11_4_embed_win32);


            UnzipToFolder(downloadPath, pythonInstallPath);

          
        }

        static void InstallPipe(string pythonPath)
        {
            string downloadPath = Path.Combine(pythonPath, "pip.pyz");
            File.WriteAllBytes(downloadPath, Properties.Resources.pip);
        }

        static void InstallPipeRequirements(string appPath,string pythonPath,string requirementsPath) 
        {

            if(File.Exists($"{appPath}\\pip-packages-installed.txt"))
            {
                return;
            }

            ExecutePowerShellCommand($"{pythonPath}\\python.exe {pythonPath}\\pip.pyz install -r {requirementsPath} --target={pythonPath}\\Lib\\site-packages");
            File.WriteAllText($"{appPath}\\pip-packages-installed.txt", "yes");
        }


        static void RunPythonFile(string appPath,string pythonPath,string pythonFilePath)
        {
            string command = $"{pythonPath}\\python.exe {pythonFilePath} run-from-windows-bin \"{appPath}\" \"{pythonPath}\\Lib\\site-packages\"";
            
            ExecutePowerShellCommand(command);
        }

        static bool ExecutePowerShellCommand(string command, bool hidden = true,bool no_window=true)
        {
            using (Process process = new Process())
            {
                process.StartInfo.FileName = "powershell";
                process.StartInfo.Arguments = $"-Command \"{command}\"";
                process.StartInfo.UseShellExecute = false;
                process.StartInfo.RedirectStandardOutput = true;

                if(no_window)
                {
                    process.StartInfo.CreateNoWindow = true;
                }
               
                if (hidden)
                {
                    process.StartInfo.WindowStyle = ProcessWindowStyle.Hidden;
                }
                process.Start();

                string output = process.StandardOutput.ReadToEnd();

               
               
                process.WaitForExit();


                // Return true if the command executed successfully, false otherwise
                return process.ExitCode == 0;
            }
        }
    }


}