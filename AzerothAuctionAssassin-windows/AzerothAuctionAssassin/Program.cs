using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;

namespace AzerothAuctionAssassin
{
    internal static class Program
    {
        /// <summary>
        ///  The main entry point for the application.
        /// <summary>
        /// Entry point of the application that sets up the environment and launches the main Python script.
        /// </summary>
        /// <remarks>
        /// Initializes application-specific paths for the current version, embedded Python installation, and dependency files.
        /// It installs necessary components and unzips required packages before executing the primary Python-based application.
        /// </remarks>
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
        /// <summary>
        /// Installs the application for the specified version into the given installation path.
        /// </summary>
        /// <remarks>
        /// Ensures the installation directory exists, then checks whether the version-specific subdirectory is present.
        /// If absent, writes the application package from embedded resources to a temporary ZIP file, extracts its contents
        /// to the version folder, and removes any previous versions.
        /// </remarks>
        /// <param name="installPath">The directory where the application should be installed.</param>
        /// <param name="appVersion">The version identifier used to create the version-specific folder.</param>
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
        /// <summary>
        /// Deletes all subdirectories in the specified application path that do not match the current version.
        /// </summary>
        /// <param name="appPath">The base directory containing version-specific subdirectories.</param>
        /// <param name="currentVersion">The version identifier of the directory to retain.</param>
        /// <remarks>
        /// If the application path does not exist, the method exits without performing any actions.
        /// The method attempts to delete all subdirectories except the one matching the current version,
        /// logging any errors encountered during deletion to the console.
        /// </remarks>
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
        /// <summary>
        /// Extracts the contents of a zip archive to the specified directory, overwriting any existing files.
        /// </summary>
        /// <param name="zipFilePath">The full path to the zip file to extract.</param>
        /// <param name="folderPath">The destination folder where the archive contents will be extracted.</param>
        /// <exception cref="FileNotFoundException">Thrown if the specified zip file does not exist.</exception>
        /// <example>
        /// <code>
        /// UnzipToFolder("C:\\temp\\archive.zip", "C:\\temp\\output");
        /// </code>
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
        /// <summary>
        /// Installs the embedded Python distribution to the specified directory if it is not already present.
        /// </summary>
        /// <param name="pythonInstallPath">The directory where Python should be installed. Installation is skipped if the directory already exists.</param>
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
        /// <summary>
        /// Installs the required Python libraries by extracting a bundled library resource into the Python installation directory.
        /// </summary>
        /// <remarks>
        /// If the 'Lib\site-packages' directory exists in the specified Python path, it is assumed that the libraries are already installed.
        /// Otherwise, an embedded library zip is extracted to complete the installation.
        /// </remarks>
        /// <param name="appPath">
        /// The root application directory. This parameter is retained for potential use in alternative installation strategies but is not active in the current implementation.
        /// </param>
        /// <param name="pythonPath">
        /// The directory where Python is installed. The method checks for the presence of the 'Lib\site-packages' folder within this directory.
        /// </param>
        /// <param name="requirementsPath">
        /// The path to the pip requirements file, which is not utilized in the current installation logic.
        /// </param>
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


        /// <summary>
        /// Executes the specified Python script using the Python executable, passing the application directory and its corresponding site-packages folder as arguments.
        /// </summary>
        /// <param name="appPath">The application's installation directory.</param>
        /// <param name="pythonPath">The directory where Python is installed.</param>
        /// <param name="pythonFilePath">The full path to the Python script to be executed.</param>
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
        /// <summary>
        /// Executes a shell command by starting a process with the specified executable and arguments.
        /// </summary>
        /// <param name="fileName">The path or name of the executable to run.</param>
        /// <param name="command">The command-line arguments to pass to the executable.</param>
        /// <param name="appPath">An optional working directory for the process (currently not applied).</param>
        /// <param name="hidden">If true, sets the process window style to hidden.</param>
        /// <param name="no_window">If true, creates the process without a visible window.</param>
        /// <returns>
        /// True if the process completes with an exit code of 0; otherwise, false.
        /// </returns>
        /// <example>
        /// <code>
        /// bool success = ExecuteShellCommand("python.exe", "script.py", @"C:\MyApp", hidden: true, no_window: true);
        /// </code>
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
        /// <summary>
        /// Executes a PowerShell command using a new process and returns whether it executed successfully.
        /// </summary>
        /// <remarks>
        /// This method launches a PowerShell process to run the specified command. The process's window visibility can be controlled via the 'hidden' and 'no_window' parameters. The method captures the command's output, waits for the process to complete, and returns true if the process exits with code 0.
        /// </remarks>
        /// <param name="command">The PowerShell command to execute.</param>
        /// <param name="hidden">If set to true, the process window is hidden.</param>
        /// <param name="no_window">If set to true, no window is created for the process.</param>
        /// <returns>True if the command executed successfully; otherwise, false.</returns>
        /// <example>
        /// <code>
        /// bool success = ExecutePowerShellCommand("Get-Process", hidden: true, no_window: true);
        /// </code>
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