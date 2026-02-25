import React, { useState } from "react";

export default function AuthPage() {
  const [isRegister, setIsRegister] = useState(false);

  // --- LOGIN STATE ---
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // --- REGISTER STATE ---
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [registerLoading, setRegisterLoading] = useState(false);
  
  // --- VALIDATION ERRORS ---
  const [registerErrors, setRegisterErrors] = useState({
    username: "",
    email: "",
    password: ""
  });

  // --- VALIDATION FUNCTIONS ---
  const validateUsername = (username) => {
    if (username.length < 3) {
      return "Username must be at least 3 characters";
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      return "Only letters, numbers, and underscores allowed";
    }
    return "";
  };

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return "Please enter a valid email address";
    }
    return "";
  };

  const validatePassword = (password) => {
    if (password.length < 6) {
      return "Password must be at least 6 characters";
    }
    if (!/[A-Z]/.test(password)) {
      return "Must contain at least one uppercase letter";
    }
    if (!/[a-z]/.test(password)) {
      return "Must contain at least one lowercase letter";
    }
    if (!/\d/.test(password)) {
      return "Must contain at least one number";
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      return "Must contain at least one special character";
    }
    return "";
  };

  // --- VALIDATION HANDLERS ---
  const handleUsernameChange = (e) => {
    const value = e.target.value;
    setNewUsername(value);
    setRegisterErrors(prev => ({
      ...prev,
      username: validateUsername(value)
    }));
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setNewEmail(value);
    setRegisterErrors(prev => ({
      ...prev,
      email: validateEmail(value)
    }));
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setNewPassword(value);
    setRegisterErrors(prev => ({
      ...prev,
      password: validatePassword(value)
    }));
  };

  // --- LOGIN HANDLER ---
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginUsername || !loginPassword) {
      alert("Please enter both username and password");
      return;
    }
    
    setLoginLoading(true);
    try {
      console.log("🔐 Attempting login for:", loginUsername);
      
      const res = await fetch("http://localhost:5000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: loginUsername,
          password: loginPassword,
        }),
        credentials: 'include'
      });
      
      console.log("Login response status:", res.status);
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP error! status: ${res.status}, message: ${text}`);
      }
      
      const data = await res.json();
      console.log("Login response data:", data);
      
      if (data.success) {
        localStorage.setItem('username', loginUsername);
        localStorage.setItem('isLoggedIn', 'true');
        
        console.log("✅ Login successful, verifying session...");
        
        try {
          const sessionRes = await fetch('http://localhost:5000/check-session', {
            credentials: 'include'
          });
          const sessionData = await sessionRes.json();
          
          if (sessionData.loggedIn) {
            console.log(`✅ Session verified for ${sessionData.username}`);
            window.location.href = "/skills";
          } else {
            console.error("❌ Session not set properly");
            alert("Login succeeded but session not set. Please try again.");
          }
        } catch (sessionErr) {
          console.error("Session check failed:", sessionErr);
          window.location.href = "/skills";
        }
      } else {
        alert("Login failed. Please check your credentials.");
      }
    } catch (err) {
      console.error("Login fetch failed:", err);
      alert("Login failed. Could not reach server.");
    } finally {
      setLoginLoading(false);
    }
  };

  // --- REGISTER HANDLER ---
  const handleRegister = async (e) => {
    e.preventDefault();
    
    // Validate all fields
    const usernameError = validateUsername(newUsername);
    const emailError = validateEmail(newEmail);
    const passwordError = validatePassword(newPassword);
    
    setRegisterErrors({
      username: usernameError,
      email: emailError,
      password: passwordError
    });
    
    // Check if any errors exist
    if (usernameError || emailError || passwordError) {
      alert("Please fix the validation errors before submitting.");
      return;
    }
    
    setRegisterLoading(true);
    try {
      const res = await fetch("http://localhost:5000/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
          email: newEmail,
        }),
      });
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP error! status: ${res.status}, message: ${text}`);
      }
      
      const data = await res.json();
      
      if (data.error) {
        if (data.error.includes("username") || data.error.includes("Username")) {
          setRegisterErrors(prev => ({
            ...prev,
            username: "Username already exists"
          }));
          alert("Username is already taken. Please choose another.");
        } else if (data.error.includes("email") || data.error.includes("Email")) {
          setRegisterErrors(prev => ({
            ...prev,
            email: "Email already registered"
          }));
          alert("Email is already registered. Please use another email.");
        } else {
          alert(data.error || "Registration failed");
        }
        return;
      }
      
      alert(data.message || "Registration successful!");
      
      setIsRegister(false);
      setNewUsername("");
      setNewPassword("");
      setNewEmail("");
      setRegisterErrors({
        username: "",
        email: "",
        password: ""
      });
      
    } catch (err) {
      console.error("Register fetch failed:", err);
      alert("Registration failed. Could not reach server.");
    } finally {
      setRegisterLoading(false);
    }
  };

  // --- TEST LOGIN (for development) ---
  const handleTestLogin = () => {
    setLoginUsername("testuser");
    setLoginPassword("testpass");
  };

  // Check if registration form is valid
  const isRegisterFormValid = () => {
    return newUsername && 
           newEmail && 
           newPassword && 
           !registerErrors.username && 
           !registerErrors.email && 
           !registerErrors.password;
  };

  return (
    <>
      <style>{`
        :root {
          --accent1: #6a11cb;
          --accent2: #2575fc;
          --error: #e74c3c;
          --success: #2ecc71;
        }

        body, html, #root {
          height: 100%;
          margin: 0;
          font-family: "Segoe UI", sans-serif;
          background: linear-gradient(135deg, var(--accent1), var(--accent2));
          overflow: hidden;
        }

        .auth-page {
          height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 20px;
          overflow: auto;
        }

        .auth-box {
          width: 480px;
          height: 560px;
          background: rgba(255,255,255,0.97);
          border-radius: 25px;
          padding: 0;
          box-shadow: 0 22px 50px rgba(0,0,0,0.28);
          overflow: hidden;
          position: relative;
        }

        .slider {
          width: 960px;
          height: 100%;
          display: flex;
          transition: transform 0.55s ease;
        }

        .slider.move-left {
          transform: translateX(-480px);
        }

        h2 {
          margin-bottom: 10px;
          font-size: 28px;
          color: #5807afff;
        }

        .sub {
          margin-top: 0;
          margin-bottom: 22px;
          font-size: 15px;
          color: #444;
        }

        .panel {
          width: 480px;
          height: 100%;
          padding: 40px;
          box-sizing: border-box;
          overflow-y: auto;
        }

        .panel::-webkit-scrollbar {
          width: 0px;
          background: transparent;
        }

        .field, .btn {
          width: 100%;
          box-sizing: border-box;
        }

        .field {
          width: 100%;
          padding: 12px 16px;
          margin-bottom: 5px;
          font-size: 16px;
          border-radius: 10px;
          border: 1px solid #ddd;
          background: #fff;
          outline: none;
          color: #333;
          box-sizing: border-box;
          transition: all 0.3s;
        }

        .field:focus {
          border-color: var(--accent1);
          box-shadow: 0 0 0 2px rgba(106, 17, 203, 0.2);
        }

        .field.error {
          border-color: var(--error);
        }

        .field.valid {
          border-color: var(--success);
        }

        .error-text {
          color: var(--error);
          font-size: 13px;
          margin-bottom: 15px;
          min-height: 16px;
          display: flex;
          align-items: center;
          padding-left: 4px;
        }

        .btn {
          width: 100%;
          padding: 14px;
          border: none;
          border-radius: 14px;
          background: linear-gradient(135deg, var(--accent1), var(--accent2));
          color: white;
          font-size: 17px;
          font-weight: 600;
          cursor: pointer;
          margin-top: 5px;
          box-sizing: border-box;
          transition: all 0.3s;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          background: #cccccc;
        }

        .btn:not(:disabled):hover {
          opacity: 0.9;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(106, 17, 203, 0.3);
        }

        .switch {
          text-align: center;
          margin-top: 20px;
          font-size: 15px;
          color: #333;
        }

        .switch span {
          color: var(--accent1);
          cursor: pointer;
          font-weight: 700;
          margin-left: 5px;
          text-decoration: underline;
        }
      `}</style>

      <div className="auth-page">
        <div className="auth-box">
          <div className={`slider ${isRegister ? "move-left" : ""}`}>

            {/* LOGIN PANEL */}
            <div className="panel">
              <h2>Welcome Back</h2>
              <p className="sub">Sign in to your account</p>

              <input
                className="field"
                type="text"
                placeholder="Username"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                disabled={loginLoading}
              />
              
              <input
                className="field"
                type="password"
                placeholder="Password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                disabled={loginLoading}
              />

              <button 
                className="btn" 
                onClick={handleLogin}
                disabled={loginLoading || !loginUsername || !loginPassword}
              >
                {loginLoading ? "Logging in..." : "Login"}
              </button>

              <button 
                className="btn" 
                onClick={handleTestLogin}
                disabled={loginLoading}
                style={{ 
                  marginTop: '10px',
                  background: 'linear-gradient(135deg, #ff7e5f, #feb47b)'
                }}
              >
                Use Test Account (testuser/testpass)
              </button>

              <p className="switch">
                New here? <span onClick={() => setIsRegister(true)}>Create account</span>
              </p>
            </div>

            {/* REGISTER PANEL */}
            <div className="panel">
              <h2>Create Account</h2>
              <p className="sub">Join us — it's quick!</p>

              {/* Username Field */}
              <input
                className={`field ${registerErrors.username ? 'error' : newUsername && !registerErrors.username ? 'valid' : ''}`}
                type="text"
                placeholder="Username"
                value={newUsername}
                onChange={handleUsernameChange}
                disabled={registerLoading}
              />
              <div className="error-text">
                {registerErrors.username}
              </div>

              {/* Email Field */}
              <input
                className={`field ${registerErrors.email ? 'error' : newEmail && !registerErrors.email ? 'valid' : ''}`}
                type="email"
                placeholder="Email"
                value={newEmail}
                onChange={handleEmailChange}
                disabled={registerLoading}
              />
              <div className="error-text">
                {registerErrors.email}
              </div>

              {/* Password Field */}
              <input
                className={`field ${registerErrors.password ? 'error' : newPassword && !registerErrors.password ? 'valid' : ''}`}
                type="password"
                placeholder="Password"
                value={newPassword}
                onChange={handlePasswordChange}
                disabled={registerLoading}
              />
              
              <div className="error-text">
                {registerErrors.password}
              </div>

              <button 
                className="btn" 
                onClick={handleRegister}
                disabled={registerLoading || !isRegisterFormValid()}
              >
                {registerLoading ? "Registering..." : "Register"}
              </button>

              <p className="switch">
                Already have an account? <span onClick={() => {
                  setIsRegister(false);
                  setNewUsername("");
                  setNewPassword("");
                  setNewEmail("");
                  setRegisterErrors({
                    username: "",
                    email: "",
                    password: ""
                  });
                }}>Sign in</span>
              </p>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}