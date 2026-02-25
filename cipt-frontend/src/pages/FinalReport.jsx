import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { saveAs } from 'file-saver';

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

const FinalReport = () => {
  const navigate = useNavigate();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [error, setError] = useState("");
  const [userInfo, setUserInfo] = useState(null);
  const [countdown, setCountdown] = useState(10);
  const [pdfUrl, setPdfUrl] = useState("");
  const [downloadReady, setDownloadReady] = useState(false);
  const [reportProgress, setReportProgress] = useState(0);
  
  // NEW STATES
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [hasSessions, setHasSessions] = useState(false);

  // Fetch user info and sessions on component mount
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await axios.get(
          `${API_BASE_URL}/user-info`,
          { withCredentials: true }
        );

        if (response.data.success) {
          setUserInfo(response.data.user);
          console.log("User info fetched:", response.data.user);
        }
      } catch (err) {
        console.error("Error fetching user info:", err);
        // Try to get username from localStorage
        const storedUsername = localStorage.getItem("username");
        if (storedUsername) {
          setUserInfo({
            username: storedUsername,
            email: localStorage.getItem("email") || `${storedUsername}@example.com`
          });
          console.log("Using stored username:", storedUsername);
        }
      }
    };

    const fetchSessions = async () => {
      setIsLoadingSessions(true);
      try {
        console.log("Fetching sessions from:", `${API_BASE_URL}/available-sessions`);
        const response = await axios.get(
          `${API_BASE_URL}/available-sessions`,
          { withCredentials: true }
        );
        
        console.log("Sessions response:", response.data);
        
        if (response.data.success) {
          setSessions(response.data.sessions || []);
          setHasSessions(response.data.sessions?.length > 0);
          
          // Auto-select the most recent session
          if (response.data.sessions && response.data.sessions.length > 0) {
            setSelectedSessionId(response.data.sessions[0].session_id);
            console.log("Auto-selected session:", response.data.sessions[0].session_id);
          }
        }
      } catch (err) {
        console.error("Error fetching sessions:", err);
        console.error("Error details:", err.response?.data || err.message);
      } finally {
        setIsLoadingSessions(false);
      }
    };

    fetchUserInfo();
    fetchSessions();
  }, []);

  // Countdown effect
  useEffect(() => {
    let timer;
    if (generated && countdown > 0) {
      timer = setTimeout(() => {
        setCountdown((prevCountdown) => prevCountdown - 1);
      }, 1000);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [generated, countdown]);

  // Progress simulation effect
  useEffect(() => {
    let progressTimer;
    if (isGenerating) {
      progressTimer = setInterval(() => {
        setReportProgress((prev) => {
          // Simulate progress: 0-80% quickly, then slow down
          if (prev < 80) {
            return prev + Math.random() * 10;
          } else if (prev < 95) {
            return prev + Math.random() * 2;
          } else if (prev < 100) {
            return prev + 0.5;
          }
          return prev;
        });
      }, 500);
    } else {
      setReportProgress(0);
    }

    return () => {
      if (progressTimer) clearInterval(progressTimer);
    };
  }, [isGenerating]);

  // Handle download PDF function
  const handleDownloadPDF = useCallback(() => {
    if (pdfUrl) {
      const timestamp = new Date().toISOString().split('T')[0];
      const username = userInfo?.username || localStorage.getItem("username") || "User";
      const filename = `interview_report_${username}_${timestamp}.pdf`;

      saveAs(pdfUrl, filename);
    }
  }, [pdfUrl, userInfo]);

  const handleGenerateReport = useCallback(async () => {
    // Check if session is selected
    if (!selectedSessionId) {
      setError("Please select a session to analyze");
      return;
    }

    setIsGenerating(true);
    setError("");
    setDownloadReady(false);
    setPdfUrl("");

    try {
      // Get user info
      const username = userInfo?.username || localStorage.getItem("username") || "User";
      const email = userInfo?.email || localStorage.getItem("email") || `${username}@example.com`;

      console.log("Sending report request:", {
        username,
        email,
        sessionId: selectedSessionId
      });

      // Prepare request data with sessionId
      const requestData = {
        username: username,
        email: email,
        sessionId: selectedSessionId
      };

      // Find subject name for the selected session
      const selectedSession = sessions.find(s => s.session_id === selectedSessionId);
      if (selectedSession && selectedSession.subject_name) {
        requestData.subjectName = selectedSession.subject_name;
        console.log("Subject name:", selectedSession.subject_name);
      }

      // Send request to backend
      console.log("Sending POST request to:", `${API_BASE_URL}/generate-report`);
      const response = await axios.post(
        `${API_BASE_URL}/generate-report`,
        requestData,
        {
          withCredentials: true,
          timeout: 300000, // 5 minutes for analysis
          responseType: 'blob', // IMPORTANT: Receive PDF as blob
          headers: {
            'Content-Type': 'application/json'
          },
          onDownloadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              setReportProgress(percentCompleted);
            }
          }
        }
      );

      console.log("Backend response received");
      
      // Create blob for PDF
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const pdfUrl = URL.createObjectURL(pdfBlob);

      setPdfUrl(pdfUrl);
      setDownloadReady(true);
      setGenerated(true);
      setIsGenerating(false);
      setReportProgress(100);

      console.log("PDF generated and ready for download");

      // Save report info
      localStorage.setItem("lastReportGenerated", new Date().toISOString());
      localStorage.setItem("lastReportUrl", pdfUrl);

    } catch (err) {
      console.error("Report generation error details:", err);
      
      let errorMessage = "Network error. Please check your connection.";

      // Handle Blob error response
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          console.log("Error response text:", text.substring(0, 500));
          const jsonError = JSON.parse(text);
          if (jsonError.error) errorMessage = jsonError.error;
          else if (jsonError.message) errorMessage = jsonError.message;
          else if (jsonError.details) errorMessage = jsonError.details;
        } catch (e) {
          console.error("Error parsing error blob:", e);
          errorMessage = "Server error. Please try again.";
        }
      }
      else if (err.code === 'ECONNABORTED') {
        errorMessage = "Request timeout. The analysis is taking longer than expected.";
      } else if (err.response?.status === 400) {
        errorMessage = "Missing or invalid data. Please check your session selection.";
      } else if (err.response?.status === 401) {
        errorMessage = "Please login again to generate reports.";
        navigate("/login");
      } else if (err.response?.status === 404) {
        errorMessage = "No videos found for this session.";
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      } else if (err.message) {
        errorMessage = err.message;
      }

      console.error("Report generation error:", errorMessage);
      setError(errorMessage);
      setIsGenerating(false);
      setReportProgress(0);
    }
  }, [navigate, selectedSessionId, sessions, userInfo]);

  const formatTime = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }, []);

  const handleBackClick = () => {
    navigate("/dashboard");
  };

  const handleRetryReport = () => {
    setError("");
    handleGenerateReport();
  };

  const handleDismissError = () => {
    setError("");
  };

  const handleGoToDashboard = () => {
    navigate("/dashboard");
  };

  // Function to handle session selection
  const handleSessionChange = (e) => {
    setSelectedSessionId(e.target.value);
    console.log("Session changed to:", e.target.value);
  };

  // Function to refresh sessions
  const handleRefreshSessions = async () => {
    setIsLoadingSessions(true);
    setError("");
    try {
      console.log("Refreshing sessions...");
      const response = await axios.get(
        `${API_BASE_URL}/available-sessions`,
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setSessions(response.data.sessions || []);
        setHasSessions(response.data.sessions?.length > 0);
        
        if (response.data.sessions && response.data.sessions.length > 0) {
          setSelectedSessionId(response.data.sessions[0].session_id);
          console.log("Sessions refreshed, selected:", response.data.sessions[0].session_id);
        } else {
          console.log("No sessions found after refresh");
        }
      }
    } catch (err) {
      console.error("Error refreshing sessions:", err);
      setError("Failed to load sessions. Please check your connection.");
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // Determine if we should show the generate report button
  const canGenerateReport = hasSessions && selectedSessionId && !isLoadingSessions;

  // Debug information
  console.log("Current state:", {
    hasSessions,
    sessionsCount: sessions.length,
    selectedSessionId,
    isLoadingSessions,
    canGenerateReport
  });

  // Inline styles
  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'Arial, sans-serif',
      margin: 0,
      padding: 0,
      width: '100vw',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      overflowY: 'auto'
    },
    content: {
      textAlign: 'center',
      maxWidth: '800px',
      padding: '40px 30px',
      width: '100%',
      margin: '0 auto'
    },
    title: {
      fontSize: '3rem',
      color: 'white',
      marginBottom: '15px',
      fontWeight: 'bold',
      textShadow: '0 2px 10px rgba(0,0,0,0.2)'
    },
    subtitle: {
      fontSize: '1.2rem',
      color: 'rgba(255, 255, 255, 0.95)',
      marginBottom: '30px',
      lineHeight: '1.5'
    },
    userInfo: {
      background: 'rgba(255, 255, 255, 0.1)',
      padding: '20px',
      borderRadius: '12px',
      marginBottom: '25px',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      textAlign: 'left',
      width: '100%',
      maxWidth: '400px',
      margin: '0 auto 25px'
    },
    infoItem: {
      marginBottom: '10px',
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    },
    infoLabel: {
      color: 'rgba(255, 255, 255, 0.8)',
      fontSize: '1rem',
      fontWeight: '500',
      minWidth: '80px'
    },
    infoValue: {
      color: 'white',
      fontSize: '1rem',
      fontWeight: 'bold'
    },
    button: {
      padding: '18px 50px',
      fontSize: '1.2rem',
      background: 'white',
      color: '#667eea',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      fontWeight: 'bold',
      transition: 'all 0.3s ease',
      marginBottom: '25px',
      boxShadow: '0 6px 20px rgba(0,0,0,0.2)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '15px',
      margin: '0 auto 25px',
      minWidth: '280px'
    },
    spinner: {
      width: '20px',
      height: '20px',
      border: '3px solid rgba(102, 126, 234, 0.3)',
      borderTop: '3px solid #667eea',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite'
    },
    note: {
      color: 'rgba(255, 255, 255, 0.8)',
      fontSize: '1rem',
      marginTop: '25px',
      lineHeight: '1.5',
      maxWidth: '600px',
      marginLeft: 'auto',
      marginRight: 'auto'
    },
    errorBox: {
      background: 'rgba(220, 53, 69, 0.15)',
      padding: '20px',
      borderRadius: '10px',
      marginBottom: '25px',
      border: '1px solid rgba(220, 53, 69, 0.3)',
      backdropFilter: 'blur(10px)',
      maxWidth: '600px',
      margin: '0 auto 25px'
    },
    errorText: {
      color: '#ff6b6b',
      fontSize: '1rem',
      marginBottom: '15px',
      textAlign: 'center'
    },
    errorDismiss: {
      background: 'rgba(220, 53, 69, 0.3)',
      color: 'white',
      border: '1px solid rgba(255, 255, 255, 0.3)',
      borderRadius: '6px',
      padding: '8px 20px',
      cursor: 'pointer',
      fontSize: '0.9rem',
      fontWeight: '500',
      margin: '0 5px'
    },
    // Session selector styles
    sessionSelector: {
      background: 'rgba(255, 255, 255, 0.1)',
      padding: '25px',
      borderRadius: '12px',
      marginBottom: '25px',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      textAlign: 'left',
      maxWidth: '600px',
      margin: '0 auto 25px'
    },
    sessionTitle: {
      color: 'white',
      fontSize: '1.3rem',
      marginBottom: '15px',
      fontWeight: 'bold',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    },
    sessionSelect: {
      width: '100%',
      padding: '12px 15px',
      borderRadius: '8px',
      border: '1px solid rgba(255, 255, 255, 0.3)',
      background: 'rgba(0, 0, 0, 0.2)',
      color: 'white',
      fontSize: '1rem',
      marginBottom: '15px'
    },
    sessionOption: {
      background: '#667eea',
      color: 'white',
      padding: '10px'
    },
    sessionInfo: {
      color: 'rgba(255, 255, 255, 0.9)',
      fontSize: '0.9rem',
      marginTop: '10px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    },
    refreshButton: {
      background: 'rgba(255, 255, 255, 0.1)',
      color: 'white',
      border: '1px solid rgba(255, 255, 255, 0.3)',
      borderRadius: '6px',
      padding: '6px 12px',
      cursor: 'pointer',
      fontSize: '0.8rem',
      display: 'flex',
      alignItems: 'center',
      gap: '5px'
    },
    // Status indicator
    statusIndicator: {
      background: canGenerateReport 
        ? 'rgba(76, 175, 80, 0.15)' 
        : isLoadingSessions 
          ? 'rgba(33, 150, 243, 0.15)' 
          : 'rgba(255, 193, 7, 0.15)',
      padding: '15px',
      borderRadius: '10px',
      marginBottom: '25px',
      border: canGenerateReport 
        ? '1px solid rgba(76, 175, 80, 0.3)' 
        : isLoadingSessions 
          ? '1px solid rgba(33, 150, 243, 0.3)' 
          : '1px solid rgba(255, 193, 7, 0.3)',
      backdropFilter: 'blur(5px)',
      maxWidth: '600px',
      margin: '0 auto 25px'
    },
    statusText: {
      color: canGenerateReport 
        ? '#4CAF50' 
        : isLoadingSessions 
          ? '#2196F3' 
          : '#FFC107',
      fontSize: '1rem',
      margin: 0,
      fontWeight: '500',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '10px'
    },
    // Action buttons
    actionButton: {
      padding: '15px 40px',
      fontSize: '1.1rem',
      background: 'linear-gradient(135deg, #2196F3, #0D47A1)',
      color: 'white',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      fontWeight: 'bold',
      transition: 'all 0.3s ease',
      margin: '15px auto',
      display: 'block',
      boxShadow: '0 4px 15px rgba(33, 150, 243, 0.4)',
      minWidth: '250px'
    },
    // Progress and analysis
    progressBar: {
      height: '8px',
      background: 'rgba(255, 255, 255, 0.1)',
      borderRadius: '4px',
      overflow: 'hidden',
      margin: '25px auto',
      maxWidth: '500px'
    },
    progressFill: {
      height: '100%',
      background: 'linear-gradient(90deg, #4CAF50, #8BC34A)',
      borderRadius: '4px',
      transition: 'width 0.3s ease',
      width: `${reportProgress}%`
    },
    progressText: {
      color: 'rgba(255, 255, 255, 0.9)',
      fontSize: '0.9rem',
      marginTop: '5px',
      textAlign: 'center'
    },
    // Analysis steps
    analysisSteps: {
      background: 'rgba(255, 255, 255, 0.08)',
      padding: '20px',
      borderRadius: '10px',
      marginBottom: '25px',
      textAlign: 'left',
      maxWidth: '500px',
      margin: '0 auto 25px'
    },
    analysisStep: {
      color: 'rgba(255, 255, 255, 0.9)',
      fontSize: '0.95rem',
      marginBottom: '10px',
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    },
    stepIcon: {
      fontSize: '1rem',
      minWidth: '20px'
    }
  };

  // Add CSS animations
  const styleTag = `
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    @keyframes float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-10px); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
  `;

  return (
    <>
      <style>{styleTag}</style>
      <div style={styles.container}>
        {!generated ? (
          <div style={styles.content}>
            <h1 style={styles.title}>Interview Analysis Report</h1>
            <p style={styles.subtitle}>
              Generate a comprehensive report of your interview performance
            </p>

            {/* Status Indicator */}
            <div style={styles.statusIndicator}>
              <p style={styles.statusText}>
                {isLoadingSessions ? (
                  <>
                    <span style={styles.spinner}></span>
                    Loading interview sessions...
                  </>
                ) : hasSessions ? (
                  <>
                    <span style={{color: '#4CAF50'}}>✓</span> Found {sessions.length} interview session{sessions.length > 1 ? 's' : ''}
                  </>
                ) : (
                  <>
                    <span style={{color: '#FFC107'}}>!</span> No interview sessions found
                  </>
                )}
              </p>
            </div>

            {/* User Info */}
            {userInfo && (
              <div style={styles.userInfo}>
                <div style={styles.infoItem}>
                  <span style={styles.infoLabel}>User:</span>
                  <span style={styles.infoValue}>{userInfo.username}</span>
                </div>
                {userInfo.email && (
                  <div style={styles.infoItem}>
                    <span style={styles.infoLabel}>Email:</span>
                    <span style={styles.infoValue}>{userInfo.email}</span>
                  </div>
                )}
              </div>
            )}

            {/* Session Selector - Only show if we have sessions */}
            {hasSessions && (
              <div style={styles.sessionSelector}>
                <div style={styles.sessionTitle}>
                  Select Interview Session
                  <button onClick={handleRefreshSessions} style={styles.refreshButton}>
                    Refresh
                  </button>
                </div>
                
                <select 
                  value={selectedSessionId} 
                  onChange={handleSessionChange}
                  style={styles.sessionSelect}
                >
                  {sessions.map((session, index) => (
                    <option 
                      key={session.session_id} 
                      value={session.session_id}
                      style={styles.sessionOption}
                    >
                      Session {index + 1}: {session.subject_name || 'Interview'} 
                      ({session.question_count || 0} questions)
                    </option>
                  ))}
                </select>
                
                {selectedSessionId && (
                  <div style={styles.sessionInfo}>
                    <span>Selected: {selectedSessionId}</span>
                    <span>
                      {sessions.find(s => s.session_id === selectedSessionId)?.question_count || 0} questions
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div style={styles.errorBox}>
                <p style={styles.errorText}>{error}</p>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                  <button
                    onClick={handleDismissError}
                    style={styles.errorDismiss}
                  >
                    Dismiss
                  </button>
                  {error.includes("session") && (
                    <button
                      onClick={handleRefreshSessions}
                      style={{
                        ...styles.errorDismiss,
                        background: 'rgba(255, 193, 7, 0.3)'
                      }}
                    >
                      Refresh Sessions
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Show analysis steps when generating */}
            {isGenerating && (
              <>
                <div style={styles.analysisSteps}>
                  <div style={styles.analysisStep}>
                    <span style={styles.stepIcon}>
                      {reportProgress > 20 ? "✓" : "..."}
                    </span>
                    Downloading videos from AWS S3...
                  </div>
                  <div style={styles.analysisStep}>
                    <span style={styles.stepIcon}>
                      {reportProgress > 40 ? "✓" : "..."}
                    </span>
                    Analyzing eye contact and gaze...
                  </div>
                  <div style={styles.analysisStep}>
                    <span style={styles.stepIcon}>
                      {reportProgress > 60 ? "✓" : "..."}
                    </span>
                    Analyzing body posture...
                  </div>
                  <div style={styles.analysisStep}>
                    <span style={styles.stepIcon}>
                      {reportProgress > 80 ? "✓" : "..."}
                    </span>
                    Analyzing facial expressions...
                  </div>
                  <div style={styles.analysisStep}>
                    <span style={styles.stepIcon}>
                      {reportProgress > 95 ? "✓" : "..."}
                    </span>
                    Generating PDF report...
                  </div>
                </div>

                {/* Progress bar */}
                <div style={styles.progressBar}>
                  <div style={styles.progressFill}></div>
                  <div style={styles.progressText}>
                    {Math.round(reportProgress)}% complete
                  </div>
                </div>
              </>
            )}

            {/* Action Buttons */}
            {!hasSessions ? (
              // No sessions - prompt to complete interview
              <>
                <button
                  onClick={handleGoToDashboard}
                  style={styles.actionButton}
                >
                  Go to Dashboard to Start Interview
                </button>
                <button
                  onClick={handleRefreshSessions}
                  style={{
                    ...styles.actionButton,
                    background: 'linear-gradient(135deg, #FF9800, #F57C00)'
                  }}
                >
                  Check for Sessions Again
                </button>
              </>
            ) : canGenerateReport ? (
              // Has sessions - show generate report button
              <button
                onClick={handleGenerateReport}
                style={{
                  ...styles.button,
                  ...(isGenerating ? {
                    opacity: 0.7,
                    cursor: 'not-allowed',
                    background: 'rgba(255, 255, 255, 0.7)'
                  } : {})
                }}
                disabled={isGenerating}
              >
                {isGenerating ? (
                  <>
                    <div style={styles.spinner}></div>
                    Generating Report... {Math.round(reportProgress)}%
                  </>
                ) : (
                  "Generate Analysis Report"
                )}
              </button>
            ) : (
              // Loading or no selection
              <button
                style={{
                  ...styles.button,
                  opacity: 0.5,
                  cursor: 'not-allowed'
                }}
                disabled
              >
                {isLoadingSessions ? "Loading..." : "Select a session above"}
              </button>
            )}

            {/* Information Note */}
            <p style={styles.note}>
              {hasSessions
                ? "The report will analyze your posture, eye contact, facial expressions, and speech patterns to provide comprehensive feedback."
                : "Complete an interview session from the dashboard to generate your performance report."}
            </p>
          </div>
        ) : (
          // Report Generated View
          <div style={styles.content}>
            <h1 style={styles.title}>Report Ready!</h1>
            <p style={styles.subtitle}>
              Your interview analysis report has been generated
            </p>

            <div style={{
              background: 'rgba(255, 255, 255, 0.1)',
              padding: '40px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              maxWidth: '500px',
              margin: '0 auto 30px'
            }}>
              <div style={{
                fontSize: '4rem',
                marginBottom: '20px',
                animation: 'float 3s ease-in-out infinite',
                color: '#4CAF50'
              }}>
                ✓
              </div>

              <h2 style={{
                color: 'white',
                fontSize: '1.8rem',
                marginBottom: '15px'
              }}>
                Analysis Complete
              </h2>

              <p style={{
                color: 'rgba(255, 255, 255, 0.9)',
                fontSize: '1.1rem',
                marginBottom: '25px',
                lineHeight: '1.5'
              }}>
                Your comprehensive interview analysis report is ready for download.
              </p>

              {downloadReady ? (
                <>
                  <button
                    onClick={handleDownloadPDF}
                    style={{
                      ...styles.button,
                      background: 'linear-gradient(135deg, #4CAF50, #2E7D32)',
                      color: 'white',
                      marginBottom: '20px'
                    }}
                  >
                    Download PDF Report
                  </button>

                  <div style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px'
                  }}>
                    <p style={{
                      color: 'white',
                      fontSize: '1rem',
                      margin: '0 0 10px 0',
                      fontWeight: 'bold'
                    }}>
                      Report Includes:
                    </p>
                    <p style={{
                      color: 'rgba(255, 255, 255, 0.8)',
                      fontSize: '0.9rem',
                      margin: 0,
                      lineHeight: '1.5'
                    }}>
                      Eye contact analysis • Body posture assessment • Facial expression tracking • 
                      Overall performance score • Detailed recommendations
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.2)',
                    padding: '20px',
                    borderRadius: '10px',
                    marginBottom: '20px',
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                  }}>
                    <p style={{
                      color: 'rgba(255, 255, 255, 0.9)',
                      fontSize: '1rem',
                      marginBottom: '10px'
                    }}>
                      Processing your video...
                    </p>
                    <div style={{
                      fontSize: '2rem',
                      color: 'white',
                      fontWeight: 'bold',
                      fontFamily: 'monospace',
                      marginBottom: '5px'
                    }}>
                      {formatTime(countdown)}
                    </div>
                    <p style={{
                      color: 'rgba(255, 255, 255, 0.7)',
                      fontSize: '0.9rem'
                    }}>
                      Estimated time remaining
                    </p>
                  </div>

                  <div style={styles.progressBar}>
                    <div style={styles.progressFill}></div>
                  </div>
                </>
              )}
            </div>

            <button
              onClick={handleBackClick}
              style={{
                ...styles.button,
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                border: '1px solid rgba(255, 255, 255, 0.3)'
              }}
            >
              ← Back to Dashboard
            </button>

            {downloadReady && (
              <p style={{
                color: 'rgba(255, 255, 255, 0.7)',
                fontSize: '0.9rem',
                marginTop: '20px'
              }}>
                Having trouble downloading?{' '}
                <button
                  onClick={handleDownloadPDF}
                  style={{
                    background: 'transparent',
                    color: 'white',
                    border: 'none',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    fontSize: '0.9rem'
                  }}
                >
                  Click here to try again
                </button>
              </p>
            )}
          </div>
        )}
      </div>
    </>
  );
};

export default FinalReport;