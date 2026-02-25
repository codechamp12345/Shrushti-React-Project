require("dotenv").config();
const { pipeline } = require("stream");
const { promisify } = require("util");

const streamPipeline = promisify(pipeline);

// ========== FIX 1: WINDOWS UNICODE FIX ==========
if (process.platform === 'win32') {
    // Fix Unicode encoding for Windows
    try {
        // Set UTF-8 for the entire process
        process.env.PYTHONIOENCODING = 'utf-8';
        process.env.NODE_OPTIONS = '--max-old-space-size=4096';
        
        // Execute chcp 65001 silently
        const { execSync } = require('child_process');
        execSync('chcp 65001 >nul 2>&1', { stdio: 'ignore' });
    } catch (e) {
        console.log('Note: Could not set UTF-8 code page');
    }
}

// ========== FIX 2: PYTHON PATH CONFIGURATION ==========
// Set Python environment variables
process.env.PYTHONUNBUFFERED = '1';
process.env.PYTHONUTF8 = '1';

console.log('Environment setup complete for Unicode support');

/* ================= CORE ================= */
const express = require("express");
const bodyParser = require("body-parser");
const sqlite3 = require("sqlite3").verbose();
const session = require("express-session");
const path = require("path");
const cors = require("cors");
const multer = require("multer");
const { S3Client, PutObjectCommand, GetObjectCommand } = require("@aws-sdk/client-s3");
const s3 = new S3Client({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY,
    secretAccessKey: process.env.AWS_SECRET_KEY,
  },
});

const fs = require("fs");
const { PythonShell } = require("python-shell");
const { URL } = require('url');

/* ================= APP ================= */
const app = express();
const db = new sqlite3.Database("users.db");

/* ================= MIDDLEWARE ================= */
app.use(cors({
  origin: "http://localhost:3000",
  credentials: true
}));

app.use(bodyParser.json({ limit: '500mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '500mb' }));

/* ================= SESSION ================= */
app.use(session({
  secret: "mySecretKey",
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: false,
    sameSite: "lax",
    maxAge: 24 * 60 * 60 * 1000
  }
}));

/* ================= STATIC ================= */
app.use("/models", express.static(path.join(__dirname, "models")));
app.use("/videos", express.static(path.join(__dirname, "videos")));



/* ================= EXTRACT SUBJECT NAME ================= */
function extractSubjectName(domain) {
  console.log(`🔍 Extracting subject from: "${domain}"`);

  if (!domain || domain === "unknown") {
    return "unknown";
  }

  const parts = domain.split('_');
  console.log(`🔍 Split parts:`, parts);

  if (parts.length >= 2) {
    const subject = parts.slice(1).join('_');
    console.log(`🔍 Subject after slice/join: "${subject}"`);

    const cleaned = subject.replace(/[^a-zA-Z0-9_]/g, '_');
    console.log(`🔍 Cleaned subject: "${cleaned}"`);

    if (cleaned && cleaned !== '_') {
      return cleaned;
    }
  }

  const subject = domain.replace(/^\d+_/, '');
  console.log(`🔍 Subject after regex: "${subject}"`);

  if (subject && subject !== domain) {
    const cleaned = subject.replace(/[^a-zA-Z0-0_]/g, '_');
    return cleaned || "unknown";
  }

  const cleaned = domain.replace(/[^a-zA-Z0-9_]/g, '_');
  return cleaned || "unknown";
}

/* ================= DATABASE SETUP ================= */
const setupDatabase = () => {
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE,
      password TEXT,
      email TEXT
    )
  `, (err) => {
    if (err) console.error("Error creating users table:", err);
    else console.log("✅ Users table ready");
  });

  db.get("SELECT name FROM sqlite_master WHERE type='table' AND name='answers'", (err, row) => {
    if (err) {
      console.error("Error checking answers table:", err);
      return;
    }

    if (!row) {
      console.log("📊 Creating answers table...");
      db.run(`
        CREATE TABLE answers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT,
          question INTEGER,
          video_filename TEXT,
          domain TEXT,
          subject_name TEXT,
          session_id TEXT,
          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `, (err) => {
        if (err) console.error("Error creating answers table:", err);
        else console.log("✅ Answers table created successfully");
      });
    } else {
      console.log("✅ Answers table already exists");
      
      // Check if session_id column exists, add it if not
      db.all("PRAGMA table_info(answers)", (err, columns) => {
        if (err) {
          console.error("Error checking columns:", err);
          return;
        }
        
        const hasSessionId = columns.some(col => col.name === 'session_id');
        if (!hasSessionId) {
          console.log("➕ Adding session_id column to answers table...");
          db.run("ALTER TABLE answers ADD COLUMN session_id TEXT", (err) => {
            if (err) console.error("Error adding session_id column:", err);
            else console.log("✅ Added session_id column to answers table");
          });
        }
      });
    }
  });

  db.run(`
    INSERT OR IGNORE INTO users (username, password, email) 
    VALUES ('testuser', 'testpass', 'test@example.com')
  `, (err) => {
    if (err) console.error("Error creating test user:", err);
    else console.log("✅ Test user ready (testuser/testpass)");
  });
};

setupDatabase();

/* ================= GET USER INFO ================= */
app.get("/get-user-info", (req, res) => {
  console.log("🔍 Get user info request");

  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  res.json({
    success: true,
    username: req.session.username
  });
});

/* ================= AUTH ================= */
app.post("/register", (req, res) => {
  const { username, password, email } = req.body;
  console.log(`📝 Registration attempt for: ${username}`);

  db.run(
    "INSERT INTO users VALUES (NULL,?,?,?)",
    [username, password, email],
    function (err) {
      if (err) {
        console.error("❌ Registration error:", err);
        res.status(400).json({ error: "User exists" });
      } else {
        console.log(`✅ User ${username} registered successfully`);
        res.json({ success: true });
      }
    }
  );
});

app.post("/login", (req, res) => {
  const { username, password } = req.body;
  console.log(`🔐 Login attempt for: ${username}`);

  db.get(
    "SELECT * FROM users WHERE username=? AND password=?",
    [username, password],
    (err, row) => {
      if (err) {
        console.error("❌ Login database error:", err);
        return res.json({ success: false, error: "Database error" });
      }

      if (row) {
        req.session.loggedIn = true;
        req.session.username = username;
        console.log(`✅ Login successful for ${username}`);
        res.json({ success: true, username: username });
      } else {
        console.log(`❌ Login failed for ${username}`);
        res.json({ success: false, error: "Invalid credentials" });
      }
    }
  );
});

/* ================= CHECK SESSION ================= */
app.get("/check-session", (req, res) => {
  console.log("🔍 Check-session called");

  if (req.session.loggedIn) {
    res.json({
      loggedIn: true,
      username: req.session.username
    });
  } else {
    res.json({ loggedIn: false });
  }
});

/* ================= USER INFO ================= */
app.get("/user-info", (req, res) => {
  console.log("🔍 User info request");

  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  db.get(
    "SELECT username, email FROM users WHERE username = ?",
    [req.session.username],
    (err, row) => {
      if (err) {
        console.error("❌ Error fetching user info:", err);
        return res.status(500).json({ error: "Database error" });
      }

      if (row) {
        res.json({
          success: true,
          user: {
            username: row.username,
            email: row.email
          }
        });
      } else {
        res.status(404).json({ error: "User not found" });
      }
    }
  );
});

/* ================= GET VIDEOS ================= */
app.get("/get-videos", (req, res) => {
  const domain = req.query.domain;
  if (!domain) {
    return res.status(400).json({ error: "Domain parameter required" });
  }

  const folder = path.join(__dirname, "videos", domain);

  if (!fs.existsSync(folder)) {
    console.log(`📁 Folder not found: ${folder}`);
    return res.status(404).json({ error: "Folder not found" });
  }

  try {
    const files = fs.readdirSync(folder);
    const videoFiles = files.filter(f =>
      /\.(mp4|mov|webm|avi|mkv|wmv)$/i.test(f)
    );

    console.log(`✅ Found ${videoFiles.length} videos in ${domain}`);
    res.json(videoFiles);
  } catch (err) {
    console.error("❌ Error reading videos:", err);
    res.status(500).json({ error: "Error reading video folder" });
  }
});

/* ================= UPLOAD ANSWER USING MULTER MEMORY STORAGE ================= */
const uploadMemory = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 500 * 1024 * 1024 // 500MB limit
  }
});

app.post("/upload-answer", uploadMemory.single("video"), async (req, res) => {
  console.log("✅ Uploading to AWS S3");

  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  console.log("📦 Received form data:", req.body);
  console.log("📁 File info:", {
    originalname: req.file.originalname,
    mimetype: req.file.mimetype,
    size: req.file.size
  });

  const { question, domain, sessionId, username: frontendUsername } = req.body;

  if (!question || !domain) {
    return res.status(400).json({
      error: "Missing required fields",
      question: question,
      domain: domain
    });
  }

  // Use session username or frontend provided username
  const username = req.session.username || frontendUsername || 'anonymous';
  const currentSessionId = sessionId || `Interview1_${new Date().toISOString().split('T')[0].replace(/-/g, '')}`;

  // Extract subject name
  const subjectName = extractSubjectName(domain);
  console.log(`🎯 Final subject name: "${subjectName}"`);

  console.log(`📁 Session Info:`, {
    sessionId: currentSessionId,
    username: username,
    subjectName: subjectName,
    question: question,
    domain: domain
  });

  // 🔴 UPDATED: Create S3 key with session folder structure
  const now = new Date();
  const timestamp =
    now.getFullYear() +
    "-" +
    (now.getMonth() + 1).toString().padStart(2, '0') +
    "-" +
    now.getDate().toString().padStart(2, '0') +
    "_" +
    now.getHours().toString().padStart(2, '0') +
    now.getMinutes().toString().padStart(2, '0') +
    now.getSeconds().toString().padStart(2, '0');

  // Format: InterviewAns/{username}/{subjectName}/{sessionId}/{filename}
  const filename = req.file.originalname || `${currentSessionId}_${subjectName}_q${question}_${timestamp}.webm`;
  const s3Key = `InterviewAns/${username}/${subjectName}/${currentSessionId}/${filename}`;

  console.log(`📁 S3 Key: ${s3Key}`);
  console.log(`👤 Username: ${username}`);
  console.log(`📚 Subject: ${subjectName}`);
  console.log(`📁 Session: ${currentSessionId}`);
  console.log(`❓ Question: ${question}`);
  console.log(`🏷️ Domain: ${domain}`);

  try {
    // Upload to S3
    const command = new PutObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME,
      Key: s3Key,
      Body: req.file.buffer,
      ContentType: req.file.mimetype,
      Metadata: {
        username: username,
        subject: subjectName,
        session: currentSessionId,
        question: question.toString(),
        domain: domain
      }
    });

    const s3Response = await s3.send(command);
    console.log("✅ File uploaded to S3 successfully");

    // S3 URL
    const s3Url = `https://${process.env.AWS_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/${s3Key}`;

    // Save to database with session_id
    db.run(
      `INSERT INTO answers (username, question, video_filename, domain, subject_name, session_id, timestamp) VALUES (?,?,?,?,?,?,?)`,
      [
        username,
        question,
        s3Key,
        domain,
        subjectName,
        currentSessionId,
        Date.now()
      ],
      function (err) {
        if (err) {
          console.error("❌ Database insert error:", err);
          return res.status(500).json({ error: "Failed to save to database: " + err.message });
        }

        console.log("✅ Record saved to database, ID:", this.lastID);

        res.json({
          success: true,
          message: "Video uploaded successfully",
          username: username,
          domain: domain,
          subject: subjectName,
          sessionId: currentSessionId,
          question: question,
          filename: filename,
          s3Key: s3Key,
          s3Url: s3Url,
          timestamp: new Date().toISOString(),
          recordId: this.lastID
        });
      }
    );

  } catch (error) {
    console.error("❌ Upload error:", error);
    res.status(500).json({ error: "Upload failed: " + error.message });
  }
});

/* ================= TEST UPLOAD (No session required) ================= */
app.post("/upload-test", uploadMemory.single("video"), async (req, res) => {
  console.log("🧪 Test upload without session");

  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const { question, domain, sessionId } = req.body;

  if (!domain) {
    return res.status(400).json({ error: "Domain is required" });
  }

  const subjectName = extractSubjectName(domain);
  const currentSessionId = sessionId || `TestSession_${Date.now()}`;
  const username = 'testuser';

  // Use session folder structure for test uploads too
  const s3Key = `InterviewAns/${username}/${subjectName}/${currentSessionId}/test_question_${question || 1}_${Date.now()}.webm`;

  try {
    const command = new PutObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME,
      Key: s3Key,
      Body: req.file.buffer,
      ContentType: req.file.mimetype
    });

    await s3.send(command);
    const s3Url = `https://${process.env.AWS_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/${s3Key}`;

    res.json({
      success: true,
      message: "Test upload successful",
      subject: subjectName,
      sessionId: currentSessionId,
      question: question || 1,
      filename: s3Key.split('/').pop(),
      s3Key: s3Key,
      s3Url: s3Url
    });
  } catch (error) {
    console.error("❌ Test upload error:", error);
    res.status(500).json({ error: "Test upload failed: " + error.message });
  }
});

/* ================= GET ALL ANSWERS ================= */
app.get("/get-answers", (req, res) => {
  db.all("SELECT * FROM answers ORDER BY timestamp DESC", (err, rows) => {
    if (err) {
      console.error("❌ Error fetching answers:", err);
      return res.status(500).json({ error: "Database error" });
    }

    console.log(`📊 Found ${rows.length} answers in database`);
    res.json(rows);
  });
});

/* ================= GET USER ANSWERS ================= */
app.get("/user-answers", (req, res) => {
  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  db.all(
    "SELECT * FROM answers WHERE username = ? ORDER BY timestamp DESC",
    [req.session.username],
    (err, rows) => {
      if (err) {
        console.error("❌ Error fetching user answers:", err);
        return res.status(500).json({ error: "Database error" });
      }

      console.log(`📊 Found ${rows.length} answers for user ${req.session.username}`);
      res.json(rows);
    }
  );
});

/* ================= GET ANSWERS BY SESSION ================= */
app.get("/session-answers/:sessionId", (req, res) => {
  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const sessionId = req.params.sessionId;

  db.all(
    "SELECT * FROM answers WHERE username = ? AND session_id = ? ORDER BY question ASC",
    [req.session.username, sessionId],
    (err, rows) => {
      if (err) {
        console.error("❌ Error fetching session answers:", err);
        return res.status(500).json({ error: "Database error" });
      }

      console.log(`📊 Found ${rows.length} answers for session ${sessionId}`);
      res.json(rows);
    }
  );
});

/* ================= GET USER SESSIONS ================= */
app.get("/user-sessions", (req, res) => {
  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  db.all(
    `SELECT DISTINCT session_id, domain, subject_name, COUNT(*) as question_count, 
            MAX(timestamp) as last_activity
     FROM answers 
     WHERE username = ? 
     GROUP BY session_id 
     ORDER BY last_activity DESC`,
    [req.session.username],
    (err, rows) => {
      if (err) {
        console.error("❌ Error fetching user sessions:", err);
        return res.status(500).json({ error: "Database error" });
      }

      console.log(`📊 Found ${rows.length} sessions for user ${req.session.username}`);
      res.json(rows);
    }
  );
});

/* ================= GENERATE REPORT (UPDATED WITH ADVANCED SUPPORT) ================= */
const { spawn } = require("child_process");


app.post("/generate-report", async (req, res) => {
  try {
    console.log("📊 Generate report request received");

    if (!req.session.loggedIn) {
      return res.status(401).json({ error: "Unauthorized" });
    }

    const { username, sessionId, subjectName, reportType = "advanced" } = req.body;

    const targetUsername = req.session.username || username;
    const targetSessionId = sessionId;
    const targetSubjectName = subjectName;

    console.log(`📊 Generating report for ${targetUsername} | ${targetSessionId}`);

    // ✅ 1. CREATE TEMP FOLDER
    const tempFolder = path.join(__dirname, "temp", targetSessionId);

    if (!fs.existsSync(tempFolder)) {
      fs.mkdirSync(tempFolder, { recursive: true });
    }

    // ✅ 2. DOWNLOAD VIDEOS FROM S3
    // You MUST adjust this prefix to match your S3 structure
    const s3Prefix = `InterviewAns/${targetUsername}/${targetSubjectName}/${targetSessionId}/`;

    console.log("🔽 Downloading videos from:", s3Prefix);

    // IMPORTANT:
    // If you store video keys in DB, fetch them first.
    // For now assuming you already have video keys array:
// Fetch video keys from database
const videoKeys = await new Promise((resolve, reject) => {
  db.all(
    "SELECT video_filename FROM answers WHERE username = ? AND session_id = ?",
    [targetUsername, targetSessionId],
    (err, rows) => {
      if (err) return reject(err);
      resolve(rows.map(r => r.video_filename));
    }
  );
});

if (!videoKeys || videoKeys.length === 0) {
  return res.status(400).json({ error: "No videos found for this session in database" });
}

console.log("📦 Video keys from DB:", videoKeys);


    for (const key of videoKeys) {
      const fileName = path.basename(key);
      const localFilePath = path.join(tempFolder, fileName);

      const command = new GetObjectCommand({
        Bucket: process.env.AWS_BUCKET_NAME,
        Key: key,
      });

      const response = await s3.send(command);
      await streamPipeline(response.Body, fs.createWriteStream(localFilePath));

      console.log("✅ Downloaded:", fileName);
    }

    console.log("📂 Files in temp:", fs.readdirSync(tempFolder));

    // ✅ 3. CHOOSE PYTHON SCRIPT
    let pythonScriptPath =
      reportType === "advanced"
        ? path.join(__dirname, "advanced_report.py")
        : path.join(__dirname, "generate_report.py");

    if (!fs.existsSync(pythonScriptPath)) {
      return res.status(500).json({ error: "Python script not found" });
    }

    // ✅ 4. SPAWN PYTHON WITH FOLDER PATH
    const pythonProcess = spawn("python", [
      pythonScriptPath,
      tempFolder,
    ]);

    let output = "";
    let errorOutput = "";

    pythonProcess.stdout.on("data", (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      errorOutput += data.toString();
      console.error("🐍 Python error:", data.toString());
    });

    pythonProcess.on("close", (code) => {
      console.log("🐍 Python exited with:", code);

      // 🔥 CLEAN TEMP FOLDER AFTER USE
      fs.rmSync(tempFolder, { recursive: true, force: true });

      if (code !== 0) {
        return res.status(500).json({
          success: false,
          error: errorOutput,
        });
      }

      return res.json({
        success: true,
        report: JSON.parse(output),
      });
    });

  } catch (err) {
    console.error("❌ Error in generate-report:", err);
    res.status(500).json({ error: "Server error" });
  }
});


// Also add this helper endpoint to list available sessions
app.get("/available-sessions", (req, res) => {
  if (!req.session.loggedIn) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  db.all(
    `SELECT DISTINCT session_id, subject_name, 
            COUNT(*) as question_count, 
            MAX(timestamp) as last_activity
     FROM answers 
     WHERE username = ? 
     GROUP BY session_id 
     ORDER BY last_activity DESC`,
    [req.session.username],
    (err, rows) => {
      if (err) {
        console.error("❌ Error fetching sessions:", err);
        return res.status(500).json({ error: "Database error" });
      }

      res.json({
        success: true,
        sessions: rows,
        count: rows.length
      });
    }
  );
});

/* ================= TEST ENDPOINT ================= */
app.get("/test", (req, res) => {
  res.json({
    status: "✅ Server is running",
    session: req.session,
    timestamp: new Date().toISOString()
  });
});

/* ================= DEBUG DOMAIN EXTRACTION ================= */
app.get("/test-extract/:domain", (req, res) => {
  const domain = req.params.domain;
  const subjectName = extractSubjectName(domain);

  res.json({
    domain: domain,
    subjectName: subjectName,
    explanation: `Extracted "${subjectName}" from "${domain}"`
  });
});

/* ================= TEST PYTHON SCRIPT ENDPOINT ================= */
app.get("/test-python", async (req, res) => {
  console.log("🧪 Testing Python environment...");

  try {
    const messages = await PythonShell.run('test_python.py', {
      mode: 'text',
      pythonPath: 'python3',
      scriptPath: __dirname,
      args: []
    });

    res.json({
      success: true,
      message: "Python test successful",
      output: messages.join('\n')
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: "Python test failed",
      details: error.message,
      suggestion: "Make sure Python 3 is installed and in PATH"
    });
  }
});

/* ================= CREATE TEST PYTHON SCRIPT ================= */
const testScriptPath = path.join(__dirname, "test_python.py");
if (!fs.existsSync(testScriptPath)) {
  const testScriptContent = `#!/usr/bin/env python3
print("✅ Python is working correctly!")
print(f"Python version: {__import__('sys').version}")
print(f"Current directory: {__import__('os').getcwd()}")
try:
    import reportlab
    print("✅ reportlab is installed")
except ImportError:
    print("❌ reportlab is NOT installed")
try:
    import matplotlib
    print("✅ matplotlib is installed")
except ImportError:
    print("❌ matplotlib is NOT installed")
try:
    import numpy
    print("✅ numpy is installed")
except ImportError:
    print("❌ numpy is NOT installed")
print("✅ All basic checks completed!")`;

  fs.writeFileSync(testScriptPath, testScriptContent);
  console.log("📝 Created test_python.py script");
}

/* ================= START ================= */
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log("🚀 Server running on http://localhost:" + PORT);
  console.log("🔍 Test endpoints:");
  console.log("  - http://localhost:5000/test");
  console.log("  - http://localhost:5000/test-python (check Python environment)");
  console.log("  - http://localhost:5000/test-extract/1_Python");
  console.log("📤 Upload endpoint:");
  console.log("  - POST http://localhost:5000/upload-answer");
  console.log("📊 Report Generation endpoint:");
  console.log("  - POST http://localhost:5000/generate-report");
  console.log("📁 Session Management endpoints:");
  console.log("  - GET http://localhost:5000/user-sessions");
  console.log("  - GET http://localhost:5000/session-answers/{sessionId}");
  console.log("📋 Important: Make sure integrated_analysis_report.py is in the backend directory");
}); 