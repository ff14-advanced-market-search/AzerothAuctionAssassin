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



            string appVersion = Properties.Resources.appVersion.Trim();
            string appPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AzerothAuctionAssassin");
            string currentVersionPath = Path.Combine(appPath, appVersion);
            string pythonPath = Path.Combine(currentVersionPath, "python-embedded");
            string requirementsPath = $"{currentVersionPath}\\requirements.txt";
            string mainPythonFilePath = $"{currentVersionPath}\\AzerothAuctionAssassin.py";




            installApp(appPath, appVersion);
            InstallPython(pythonPath);
            //InstallPipe(pythonPath); //no need for pip cuz now packages are installed and zipped during the pipeline.
            // this now unzip packages instead of installing them which will make much faster at the first run.
            InstallPipeRequirements(currentVersionPath,pythonPath, requirementsPath);
            RunPythonFile(currentVersionPath,pythonPath,mainPythonFilePath);
        }


        /// <summary>
        /// Installs an application at the specified path and version, creating necessary directories and handling updates as needed.
        /// </summary>
        /// <param name="installPath">The file system path where the application should be installed.</param>
        /// <param name="appVersion">The version of the application to be installed.</param>
        /// <returns>None</returns>
        /// <example>
        /// installApp(@"C:\Apps\AzerothAuctionAssassin\", "1.0.0");
        /// // This will install the application at the specified directory, creating directories if they do not exist,
        /// // and set it to the specified version, handling any version-specific setup.
        /// </example>
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

                deleteOldVersions(installPath, appVersion);
            }
            else
            {
                return;
            }

        }

        /// <summary>
        /// Deletes all old version directories in the specified application path, retaining only the current version directory.
        /// </summary>
        /// <param name="appPath">The path to the application directory where versioned directories are stored.</param>
        /// <param name="currentVersion">The name of the directory that corresponds to the current version which should not be deleted.</param>
        /// <example>
        /// deleteOldVersions("/path/to/app", "v1.2.3");
        /// // This will delete all directories in the specified path except for "v1.2.3".
        /// </example>
        public static void deleteOldVersions(string appPath, string currentVersion)
        {
            if (!Directory.Exists(appPath)) return;

            // Get all the directories in the application path
            var directoryInfo = new DirectoryInfo(appPath);
            var directories = directoryInfo.GetDirectories();

            foreach (var directory in directories)
            {
                // If the directory name is not the current version, delete it
                if (directory.Name != currentVersion)
                {
                    try
                    {
                        directory.Delete(true); // true to remove directories, subdirectories, and files
                       
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error deleting old version {directory.Name}: {ex.Message}");
                    }
                }
            }
        }

        /// <summary>
        /// Extracts the contents of a specified zip file to a specified directory.
        /// </summary>
        /// <param name="zipFilePath">The path to the zip file that needs to be extracted.</param>
        /// <param name="folderPath">The destination folder path where the contents will be extracted.</param>
        /// <exception cref="FileNotFoundException">Thrown when the specified zip file does not exist.</exception>
        /// <example>
        /// UnzipToFolder("example.zip", "outputDirectory");
        /// </example>
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



        /// <summary>
        /// Installs Python to the specified installation path if it is not already present.
        /// </summary>
        /// <param name="pythonInstallPath">The directory path where Python should be installed.</param>
        /// <example>
        /// InstallPython("C:\\Path\\To\\Install\\Python");
        /// </example>
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
            File.WriteAllBytes(downloadPath, Properties.Resources.python);


            UnzipToFolder(downloadPath, pythonInstallPath);

          
        }

        /*
        static void InstallPipe(string pythonPath)
        {
            string downloadPath = Path.Combine(pythonPath, "pip.pyz");
            File.WriteAllBytes(downloadPath, Properties.Resources.pip);
        }
        */

        /// <summary>
        /// Installs the necessary pip package requirements for the application environment.
        /// </summary>
        /// <param name="appPath">The file path of the application where installation status will be noted.</param>
        /// <param name="pythonPath">The file path where Python is installed, which is used for executing pip commands.</param>
        /// <param name="requirementsPath">The file path containing the requirements.txt specifying necessary packages.</param>
        /// <remarks>
        /// This method ensures that the required pip packages are installed within the specified Python environment.
        /// If the packages have already been installed, as indicated by a presence of a confirmation file at appPath, the method exits.
        /// Otherwise, it attempts to unzip a library zip file to the Python path.
        /// </remarks>
        /// <example>
        /// InstallPipeRequirements("C:\\MyApp", "C:\\Python39", "C:\\MyApp\\requirements.txt");
        /// // This will ensure the required Python packages are installed or attempt to extract them from a library zip.
        /// </example>
        static void InstallPipeRequirements(string appPath,string pythonPath,string requirementsPath) 
        {
            /*
            if(File.Exists($"{appPath}\\pip-packages-installed.txt"))
            {
                return;
            }

            ExecutePowerShellCommand($"{pythonPath}\\python.exe {pythonPath}\\pip.pyz install -r {requirementsPath} --target={pythonPath}\\Lib\\site-packages");
            File.WriteAllText($"{appPath}\\pip-packages-installed.txt", "yes");
            */

            if (Directory.Exists($"{pythonPath}\\Lib\\site-packages"))
            {
                return;
            }
            string downloadPath = Path.Combine(Path.GetTempPath(), "Lib.zip");
            File.WriteAllBytes(downloadPath, Properties.Resources.Lib);


            UnzipToFolder(downloadPath, $"{pythonPath}");

        }


        static void RunPythonFile(string appPath,string pythonPath,string pythonFilePath)
        {
            string command = $"{pythonFilePath} run-from-windows-bin \"{appPath}\" \"{pythonPath}\\Lib\\site-packages\"";
            
          
            ExecuteShellCommand($"{pythonPath}\\python.exe",command,appPath,false,false);
        }


        /// <summary>
        /// Executes a shell command with specified options for visibility and working directory.
        /// </summary>
        /// <param name="fileName">The name of the executable file to run.</param>
        /// <param name="command">The command line arguments to pass to the executable.</param>
        /// <param name="appPath">Optional. The working directory for the process. Defaults to an empty string.</param>
        /// <param name="hidden">Optional. Specifies whether the process should be hidden. Default is true.</param>
        /// <param name="no_window">Optional. Specifies whether the process should be run without creating a window. Default is true.</param>
        /// <returns>Returns true if the command executed successfully (exit code 0), otherwise false.</returns>
        /// <example>
        /// bool result = ExecuteShellCommand("cmd.exe", "/c dir", @"C:\", true, true);
        /// Console.WriteLine(result); // Expected output: true or false depending on the execution outcome
        /// </example>
        static bool ExecuteShellCommand(string fileName, string command, string appPath = "", bool hidden = true, bool no_window = true)
        {
            using (Process process = new Process())
            {
                process.StartInfo.FileName = fileName;
                process.StartInfo.Arguments = command;
                // setting the python process working Directory to be the same as the app dir.
               // process.StartInfo.WorkingDirectory = appPath;
              
                //process.StartInfo.UseShellExecute = false;
                //process.StartInfo.RedirectStandardOutput = true;

                if (no_window)
                {
                    process.StartInfo.CreateNoWindow = true;
                }

                if (hidden)
                {
                    process.StartInfo.WindowStyle = ProcessWindowStyle.Hidden;
                }
                process.Start();

                



                process.WaitForExit();


                // Return true if the command executed successfully, false otherwise
                return process.ExitCode == 0;
            }
        }

        /// <summary>
        /// Executes a specified PowerShell command using a new process, with options to hide the window and run without creating a new window.
        /// </summary>
        /// <param name="command">The PowerShell command string to execute.</param>
        /// <param name="hidden">A boolean indicating whether the PowerShell window should be hidden during execution. Defaults to true.</param>
        /// <param name="no_window">A boolean indicating whether to avoid creating a new window for the process. Defaults to true.</param>
        /// <returns>True if the command executed successfully; otherwise, false.</returns>
        /// <example>
        /// bool result = ExecutePowerShellCommand("Get-Process", false, false);
        /// Console.WriteLine(result); // Expected output: True if the command is valid and executes without errors
        /// </example>
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