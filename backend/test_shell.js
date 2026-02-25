const { PythonShell } = require("python-shell");
const path = require("path");

console.log("🚀 Testing PythonShell execution...");

const scriptPath = "generate_report.py";
// Use a dummy username for testing
const args = ['--username', 'testuser'];

const options = {
    mode: 'text',
    pythonOptions: ['-u'],
    scriptPath: __dirname,
    args: args,
    pythonPath: 'python',
    env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1'
    }
};

console.log(`📂 Script: ${scriptPath}`);
console.log(`🔧 Options:`, JSON.stringify(options, null, 2));

const pyshell = new PythonShell(scriptPath, options);

pyshell.on('message', function (message) {
    console.log(`📩 Message: ${message}`);
});

pyshell.on('stderr', function (stderr) {
    console.log(`⚠️ Stderr: ${stderr}`);
});

pyshell.end(function (err, code, signal) {
    if (err) {
        console.error('❌ Error:', err);
    }
    console.log(`✅ PythonShell finished with code ${code} and signal ${signal}`);
});
