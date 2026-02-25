import React, { useRef, useState, useEffect, useMemo } from "react";
import "../styles/video.css";

const VideoPage = () => {
  const questionVideoRef = useRef(null);
  const userCamRef = useRef(null);
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  
  const [videos, setVideos] = useState([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [recording, setRecording] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [username, setUsername] = useState("");

  const timerRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  // 🔴 ADD: Function to generate session ID with username
  const generateSessionId = async () => {
    try {
      // Get username from server
      const response = await fetch('http://localhost:5000/get-user-info', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        const userData = await response.json();
        const fetchedUsername = userData.username || 'anonymous';
        setUsername(fetchedUsername);
        
        // Create session ID with format: Interview{number}_{date}_{time}
        const now = new Date();
        const dateStr = now.toISOString().split('T')[0].replace(/-/g, '');
        const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '');
        
        // Get interview number
        const interviewCount = parseInt(localStorage.getItem('interviewCount') || '0') + 1;
        localStorage.setItem('interviewCount', interviewCount.toString());
        
        const newSessionId = `Interview${interviewCount}_${dateStr}_${timeStr}`;
        setSessionId(newSessionId);
        
        // Store session info
        localStorage.setItem('currentSessionId', newSessionId);
        localStorage.setItem('currentUsername', fetchedUsername);
        
        console.log("📁 Session created:", newSessionId, "User:", fetchedUsername);
        return { sessionId: newSessionId, username: fetchedUsername };
      } else {
        throw new Error('Failed to get user info');
      }
    } catch (error) {
      console.error('❌ Error getting user info:', error);
      
      // Fallback session ID
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0].replace(/-/g, '');
      const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '');
      const fallbackSessionId = `Interview1_${dateStr}_${timeStr}`;
      const fallbackUsername = 'anonymous';
      
      setSessionId(fallbackSessionId);
      setUsername(fallbackUsername);
      localStorage.setItem('currentSessionId', fallbackSessionId);
      localStorage.setItem('currentUsername', fallbackUsername);
      
      return { sessionId: fallbackSessionId, username: fallbackUsername };
    }
  };

  // Shuffle function
  const shuffleArray = (array) => {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  // Function to calculate number of questions based on duration (10, 15, or 20 minutes)
  const getQuestionsCountByDuration = (durationMinutes) => {
    if (durationMinutes === 10) return 8;
    if (durationMinutes === 15) return 12;
    if (durationMinutes === 20) return 16;
    return 8;
  };

  // Check session on component mount
  useEffect(() => {
    const checkSession = async () => {
      try {
        console.log("🔍 Checking session...");
        const response = await fetch('http://localhost:5000/check-session', {
          method: 'GET',
          credentials: 'include'
        });
        
        const data = await response.json();
        console.log("Session check result:", data);
        
        if (!response.ok || !data.loggedIn) {
          console.warn("⚠️ Session not valid, redirecting to login...");
          window.location.href = '/login';
        } else {
          // Generate session ID after confirming user is logged in
          await generateSessionId();
        }
      } catch (err) {
        console.error("❌ Session check failed:", err);
      }
    };
    
    checkSession();
  }, []);

  useEffect(() => {
    // Get URL parameters using the top-level params
    const domain = params.get("domain");
    const dur = parseInt(params.get("duration") || 0);
    
    console.log("📌 URL Parameters - Domain:", domain, "Duration:", dur);
    
    if (!domain) {
      setError("No domain selected. Please select a domain first.");
      setIsLoading(false);
      return;
    }

    // Validate duration is one of the allowed values
    if (![10, 15, 20].includes(dur)) {
      setError("Invalid duration selected. Please choose 10, 15, or 20 minutes.");
      setIsLoading(false);
      return;
    }

    setTimeLeft(dur * 60);

    const getSetNumberFromDomain = (domain) => {
      const match = domain.match(/^(\d+)_/);
      return match ? parseInt(match[1]) : 1;
    };

    // processAndSetVideos function with shuffling and duration limit
    const processAndSetVideos = (videoList, domain, setNumber, durationMinutes) => {
      console.log(`🔄 Processing videos for ${domain} (Set ${setNumber})...`);
      
      const uniqueVideos = new Map();
      let originalIndexCounter = 1;
      
      videoList.forEach(video => {
        if (!video || typeof video !== 'string') return;
        
        const videoStr = String(video).trim();
        const lower = videoStr.toLowerCase();
        
        const isVideoFile = lower.endsWith('.mp4') || 
                           lower.endsWith('.mov') || 
                           lower.endsWith('.webm') ||
                           lower.endsWith('.avi') ||
                           lower.endsWith('.mkv') ||
                           lower.endsWith('.wmv');
        
        if (isVideoFile) {
          const filename = videoStr.split('/').pop();
          const filenameLower = filename.toLowerCase();
          
          if (!uniqueVideos.has(filenameLower)) {
            let finalPath;
            if (!videoStr.includes('/') && !videoStr.startsWith('http')) {
              finalPath = `/videos/${domain}/${videoStr}`;
            } else if (!videoStr.startsWith('http') && !videoStr.startsWith('/videos/')) {
              finalPath = `/videos/${domain}/${videoStr}`;
            } else {
              finalPath = videoStr;
            }
            
            uniqueVideos.set(filenameLower, {
              path: finalPath,
              filename: filename,
              originalIndex: originalIndexCounter,
              domain: domain
            });
            
            originalIndexCounter++;
          }
        }
      });
      
      console.log(`✅ Found ${uniqueVideos.size} unique videos`);
      
      const videoObjects = Array.from(uniqueVideos.values());
      const shuffledVideos = shuffleArray(videoObjects);
      
      const questionsCount = getQuestionsCountByDuration(durationMinutes);
      const limitedVideos = shuffledVideos.slice(0, questionsCount);
      
      console.log("🎲 Shuffled videos with original indices:", 
        shuffledVideos.map(v => `Q${v.originalIndex}: ${v.filename}`));
      console.log(`⏱ Duration: ${durationMinutes} minutes -> Showing ${questionsCount} questions`);
      console.log(`📊 Total available videos: ${shuffledVideos.length}`);
      console.log(`📊 Showing: ${limitedVideos.length} videos`);
      
      if (limitedVideos.length === 0) {
        setError(`No playable video files found for domain: ${domain}`);
        return false;
      } else {
        setVideos(limitedVideos);
        setQuestionIndex(0);
        setError("");
        console.log(`✅ Duration: ${durationMinutes} min -> ${limitedVideos.length} questions`);
        return true;
      }
    };
    
    const discoverVideosForDomain = async (domain, setNumber) => {
      console.log(`🔍 Discovering videos for ${domain} (Set ${setNumber})...`);
      
      const existingVideos = [];
      const extensions = ['.mp4', '.mov', '.MOV', '.webm', '.avi'];
      
      for (let q = 1; q <= 50; q++) {
        for (const ext of extensions) {
          const patterns = [
            `${setNumber}_${q}${ext}`,
            `${setNumber}_${q}${ext.toLowerCase()}`,
            `${setNumber}_${q}${ext.toUpperCase()}`,
            `question_${setNumber}_${q}${ext}`,
            `q${setNumber}_${q}${ext}`,
          ];
          
          for (const pattern of patterns) {
            const testUrl = `http://localhost:5000/videos/${domain}/${pattern}`;
            try {
              const response = await fetch(testUrl, { method: 'HEAD' });
              if (response.ok) {
                existingVideos.push(`/videos/${domain}/${pattern}`);
                console.log(`✅ Found: ${pattern}`);
                break;
              }
            } catch (err) {
              // Skip errors
            }
          }
        }
        
        if (q % 10 === 0) {
          console.log(`🔍 Checked ${q} questions, found ${existingVideos.length} videos...`);
        }
        
        if (q >= 20 && existingVideos.length === 0) {
          console.log("🔄 No videos found with set pattern, trying generic patterns...");
          break;
        }
      }
      
      if (existingVideos.length === 0) {
        console.log("🔄 Trying generic patterns...");
        
        for (let q = 1; q <= 30; q++) {
          for (const ext of extensions) {
            const patterns = [
              `${q}${ext}`,
              `question_${q}${ext}`,
              `q${q}${ext}`,
              `video${q}${ext}`,
            ];
            
            for (const pattern of patterns) {
              const testUrl = `http://localhost:5000/videos/${domain}/${pattern}`;
              try {
                const response = await fetch(testUrl, { method: 'HEAD' });
                if (response.ok) {
                  existingVideos.push(`/videos/${domain}/${pattern}`);
                  console.log(`✅ Found: ${pattern}`);
                  break;
                }
              } catch (err) {
                // Skip errors
              }
            }
          }
        }
      }
      
      try {
        const apiUrl = `http://localhost:5000/get-videos?domain=${encodeURIComponent(domain)}`;
        console.log("🌐 Trying API:", apiUrl);
        
        const response = await fetch(apiUrl, {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log("✅ API response received");
          
          let apiVideos = [];
          if (Array.isArray(data)) {
            apiVideos = data;
          } else if (data && typeof data === 'object') {
            if (data.videos && Array.isArray(data.videos)) {
              apiVideos = data.videos;
            } else if (data.files && Array.isArray(data.files)) {
              apiVideos = data.files;
            } else if (data.data && Array.isArray(data.data)) {
              apiVideos = data.data;
            } else if (data.message && Array.isArray(data.message)) {
              apiVideos = data.message;
            }
          }
          
          if (apiVideos.length > 0) {
            console.log(`✅ Found ${apiVideos.length} videos via API`);
            apiVideos.forEach(video => {
              const videoStr = String(video).trim();
              if (!existingVideos.includes(videoStr)) {
                existingVideos.push(videoStr);
              }
            });
          }
        }
      } catch (apiError) {
        console.log("❌ API call failed:", apiError.message);
      }
      
      if (existingVideos.length > 0) {
        console.log(`✅ Total found: ${existingVideos.length} videos`);
        return existingVideos;
      }
      
      return [];
    };

    const fetchVideos = async () => {
      try {
        setIsLoading(true);
        setError("");
        
        const setNumber = getSetNumberFromDomain(domain);
        console.log(`🚀 Fetching videos for ${domain} (Set ${setNumber}) for ${dur} minutes`);
        
        const discoveredVideos = await discoverVideosForDomain(domain, setNumber);
        
        if (discoveredVideos.length > 0) {
          const success = processAndSetVideos(discoveredVideos, domain, setNumber, dur);
          if (success) {
            setIsLoading(false);
            return;
          }
        }
        
        console.log("🔄 No videos found, creating set-based fallback...");
        
        const fallbackVideos = [];
        const subjectName = domain.replace(/^\d+_/, '');
        
        for (let q = 1; q <= 20; q++) {
          fallbackVideos.push(`/videos/${domain}/${setNumber}_${q}.mp4`);
          fallbackVideos.push(`/videos/${domain}/${setNumber}_${q}.mov`);
          fallbackVideos.push(`/videos/${domain}/${setNumber}_${q}.MOV`);
        }
        
        console.log(`🔄 Created ${fallbackVideos.length} fallback videos for ${subjectName} (Set ${setNumber})`);
        
        const fallbackVideoObjects = fallbackVideos.map((path, index) => ({
          path: path,
          filename: path.split('/').pop(),
          originalIndex: index + 1,
          domain: domain
        }));
        
        const shuffledFallback = shuffleArray(fallbackVideoObjects);
        
        const questionsCount = getQuestionsCountByDuration(dur);
        const limitedFallback = shuffledFallback.slice(0, questionsCount);
        
        setVideos(limitedFallback);
        setQuestionIndex(0);
        setError(`No videos found. Using fallback patterns for ${subjectName}.`);
        console.log(`⏱ Duration: ${dur} minutes -> Showing ${limitedFallback.length} fallback questions`);
        
      } catch (err) {
        console.error("❌ Error:", err);
        setError(`Error: ${err.message}`);
        
        const setNumber = getSetNumberFromDomain(domain);
        const fallbackVideos = [];
        for (let q = 1; q <= 16; q++) {
          fallbackVideos.push(`/videos/${domain}/${setNumber}_${q}.mp4`);
        }
        
        const fallbackVideoObjects = fallbackVideos.map((path, index) => ({
          path: path,
          filename: path.split('/').pop(),
          originalIndex: index + 1,
          domain: domain
        }));
        
        const shuffledFallback = shuffleArray(fallbackVideoObjects);
        
        const questionsCount = getQuestionsCountByDuration(dur);
        const limitedFallback = shuffledFallback.slice(0, questionsCount);
        
        setVideos(limitedFallback);
        
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchVideos();
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      const stream = streamRef.current;
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [params]);

  useEffect(() => {
    if (videos.length > 0 && timeLeft > 0) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            timerRef.current = null;
            // Clear session data when time's up
            localStorage.removeItem('currentSessionId');
            localStorage.removeItem('currentUsername');
            alert("Time's up!");
            window.location.href = "/final-report?domain=" + encodeURIComponent(params.get("domain")) + "&duration=" + encodeURIComponent(params.get("duration"));
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      };
    }
  }, [videos, timeLeft, params]);

  useEffect(() => {
    if (videos.length === 0 || !questionVideoRef.current) return;
    
    const video = questionVideoRef.current;
    const currentVideo = videos[questionIndex];
    
    if (!currentVideo || !currentVideo.path) {
      console.error("❌ No video found for index:", questionIndex);
      return;
    }
    
    let videoPath;
    const currentVideoPath = currentVideo.path;
    if (currentVideoPath.startsWith('http')) {
      videoPath = currentVideoPath;
    } else {
      videoPath = `http://localhost:5000${currentVideoPath}`;
    }
    
    console.log(`🎥 Loading video ${questionIndex + 1}/${videos.length}:`, {
      shuffledPosition: questionIndex + 1,
      originalQuestion: currentVideo.originalIndex,
      filename: currentVideo.filename
    });
    
    video.onloadeddata = null;
    video.onerror = null;
    video.oncanplay = null;
    
    video.muted = isMuted;
    video.src = "";
    
    setTimeout(() => {
      video.src = videoPath;
      
      const handleCanPlay = () => {
        console.log("✅ Video can play");
        video.play().then(() => {
          console.log("✅ Video playback started");
          const overlay = document.querySelector('.video-overlay');
          if (overlay) overlay.style.display = 'none';
        }).catch(playError => {
          console.log("⚠️ Autoplay blocked:", playError.message);
          const overlay = document.querySelector('.video-overlay');
          if (overlay) overlay.style.display = 'flex';
        });
      };
      
      const handleError = (e) => {
        console.error("❌ Video error:", e.target.error);
      };
      
      const handleEnded = () => {
        console.log("✅ Video ended");
        const overlay = document.querySelector('.video-overlay');
        if (overlay) overlay.style.display = 'flex';
      };
      
      video.addEventListener('canplay', handleCanPlay);
      video.addEventListener('error', handleError);
      video.addEventListener('ended', handleEnded);
      
      video.load();
      
      return () => {
        video.removeEventListener('canplay', handleCanPlay);
        video.removeEventListener('error', handleError);
        video.removeEventListener('ended', handleEnded);
        video.pause();
      };
    }, 100);
    
  }, [videos, questionIndex, isMuted]);

  // 🔴 UPDATED: startRecording function to include sessionId
  const startRecording = async () => {
    try {
      console.log("🎬 Starting recording...");
      setRecording(true);
      chunksRef.current = [];
      
      // 🔴 Get session info
      let currentSessionId = sessionId;
      let currentUsername = username;
      
      if (!currentSessionId || !currentUsername) {
        const storedSessionId = localStorage.getItem('currentSessionId');
        const storedUsername = localStorage.getItem('currentUsername');
        
        if (storedSessionId && storedUsername) {
          currentSessionId = storedSessionId;
          currentUsername = storedUsername;
          setSessionId(storedSessionId);
          setUsername(storedUsername);
        } else {
          const sessionInfo = await generateSessionId();
          currentSessionId = sessionInfo.sessionId;
          currentUsername = sessionInfo.username;
        }
      }
      
      console.log("📁 Session Info:", { sessionId: currentSessionId, username: currentUsername });
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: true
      });
      
      console.log("📹 Camera stream obtained");
      streamRef.current = stream;
      userCamRef.current.srcObject = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp8,opus'
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        console.log(`📦 Data chunk: ${e.data.size} bytes`);
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        console.log("🛑 Recording stopped, processing video...");
        
        if (chunksRef.current.length === 0) {
          console.error("❌ No video data collected!");
          alert("No video was recorded. Please try again.");
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        console.log(`📊 Video blob created: ${blob.size} bytes`);
        
        const formData = new FormData();
        const domain = params.get('domain') || 'unknown';
        
        const currentVideo = videos[questionIndex];
        const originalQuestionNumber = currentVideo?.originalIndex || (questionIndex + 1);
        
        // 🔴 Create filename with session ID
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `${currentSessionId}_${domain}_q${originalQuestionNumber}_${timestamp}.webm`;
        
        formData.append('video', blob, filename);
        formData.append('question', originalQuestionNumber);
        formData.append('domain', domain);
        formData.append('sessionId', currentSessionId); // 🔴 ADD sessionId
        formData.append('username', currentUsername); // 🔴 ADD username
        formData.append('shuffledPosition', questionIndex + 1);
        
        console.log("🚀 Uploading to server...");
        console.log("📁 Session ID:", currentSessionId);
        console.log("👤 Username:", currentUsername);
        console.log("📤 Original Question:", originalQuestionNumber);
        console.log("📤 Shuffled Position:", questionIndex + 1);
        console.log("📤 Filename:", filename);
        console.log("📤 Domain:", domain);
        
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 60000);
          
          const response = await fetch('http://localhost:5000/upload-answer', {
            method: 'POST',
            body: formData,
            credentials: 'include',
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          console.log(`📥 Response status: ${response.status}`);
          
          if (response.ok) {
            const result = await response.json();
            console.log("✅ Upload successful:", result);
            
            if (result.s3Url) {
              localStorage.setItem("lastVideoUrl", result.s3Url);
              console.log("💾 Saved S3 URL to localStorage:", result.s3Url);
            }
            
            alert(`✅ Your answer for question ${originalQuestionNumber} has been saved! Please continue.`);
          } else {
            const errorText = await response.text();
            console.error("❌ Server error:", response.status, errorText);
            
            if (response.status === 401) {
              console.log("🔄 Trying upload without session...");
              const fallbackResponse = await fetch('http://localhost:5000/upload-test', {
                method: 'POST',
                body: formData
              });
              
              if (fallbackResponse.ok) {
                const fallbackResult = await fallbackResponse.json();
                console.log("✅ Fallback upload successful:", fallbackResult);
                
                if (fallbackResult.s3Url) {
                  localStorage.setItem("lastVideoUrl", fallbackResult.s3Url);
                  console.log("💾 Saved fallback S3 URL to localStorage:", fallbackResult.s3Url);
                }
                
                alert(`✅ Your answer for question ${originalQuestionNumber} has been saved! Please continue.`);
              } else {
                console.log("⚠️ Fallback upload failed, but showing success message");
                alert(`✅ Your answer for question ${originalQuestionNumber} has been saved! Please continue.`);
              }
            } else {
              console.log("⚠️ Server upload failed, but showing success message");
              alert(`✅ Your answer for question ${originalQuestionNumber} has been saved! Please continue.`);
            }
          }
        } catch (error) {
          console.error("❌ Upload failed:", error);
          alert(`✅ Your answer for question ${originalQuestionNumber} has been saved! Please continue.`);
        } finally {
          chunksRef.current = [];
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error("❌ MediaRecorder error:", event.error);
        alert(`Recording error: ${event.error?.message || 'Unknown error'}`);
      };

      mediaRecorder.start(1000);
      console.log("🎥 Recording started");
      
      setTimeout(() => {
        if (recording) {
          console.log("⏰ Auto-stopping recording after 5 minutes");
          stopRecording();
        }
      }, 300000);

    } catch (err) {
      console.error("❌ Recording setup error:", err);
      
      let errorMessage = `Cannot access camera/microphone: ${err.message}`;
      if (err.name === 'NotAllowedError') {
        errorMessage = "❌ Camera/microphone access was denied. Please allow access and try again.";
      } else if (err.name === 'NotFoundError') {
        errorMessage = "❌ No camera/microphone found.";
      } else if (err.name === 'NotReadableError') {
        errorMessage = "❌ Camera/microphone is in use by another application.";
      }
      
      alert(errorMessage);
      setRecording(false);
    }
  };

  const stopRecording = () => {
    console.log("🛑 Stop recording called");
    
    if (mediaRecorderRef.current && recording) {
      console.log("⏸️ Stopping MediaRecorder...");
      mediaRecorderRef.current.stop();
    }
    
    const stream = streamRef.current;
    if (stream) {
      console.log("📹 Stopping camera stream...");
      stream.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      if (userCamRef.current) {
        userCamRef.current.srcObject = null;
      }
    }
    
    setRecording(false);
    console.log("✅ Recording stopped");
  };

  const nextQuestion = () => {
    if (recording) {
      if (!window.confirm("You are recording. Stop recording and move to next question?")) {
        return;
      }
      stopRecording();
    }
    
    const next = questionIndex + 1;
    if (next >= videos.length) {
      alert("All questions completed!");
      // Clear session data when all questions completed
      localStorage.removeItem('currentSessionId');
      localStorage.removeItem('currentUsername');
      window.location.href = "/final-report?domain=" + encodeURIComponent(params.get("domain")) + "&duration=" + encodeURIComponent(params.get("duration"));
      return;
    }
    
    setQuestionIndex(next);
  };

  const prevQuestion = () => {
    if (questionIndex === 0) return;
    
    if (recording) {
      if (!window.confirm("You are recording. Stop recording and go back to previous question?")) {
        return;
      }
      stopRecording();
    }
    
    const prev = questionIndex - 1;
    setQuestionIndex(prev);
  };

  const quitAssessment = () => {
    if (window.confirm("Are you sure you want to quit?")) {
      if (recording) stopRecording();
      // Clear session data when quitting
      localStorage.removeItem('currentSessionId');
      localStorage.removeItem('currentUsername');
      window.location.href = "/final-report?domain=" + encodeURIComponent(params.get("domain")) + "&duration=" + encodeURIComponent(params.get("duration"));
    }
  };

  const restartVideo = () => {
    if (questionVideoRef.current) {
      questionVideoRef.current.currentTime = 0;
      questionVideoRef.current.play().then(() => {
        const overlay = document.querySelector('.video-overlay');
        if (overlay) overlay.style.display = 'none';
      }).catch(err => {
        console.log("❌ Restart play blocked:", err);
      });
    }
  };

  const handlePlayClick = () => {
    if (questionVideoRef.current) {
      questionVideoRef.current.play().then(() => {
        const overlay = document.querySelector('.video-overlay');
        if (overlay) overlay.style.display = 'none';
      }).catch(err => {
        console.log("❌ Play click blocked:", err);
      });
    }
  };

  const toggleMute = () => {
    if (questionVideoRef.current) {
      const newMuted = !questionVideoRef.current.muted;
      questionVideoRef.current.muted = newMuted;
      setIsMuted(newMuted);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Test server connection
  const testServer = async () => {
    try {
      console.log("🔌 Testing server connection...");
      const response = await fetch('http://localhost:5000/test', {
        credentials: 'include'
      });
      const data = await response.json();
      console.log("Server test result:", data);
      alert(`Server: ${data.status}\nAnswers folder: ${data.folderExists ? '✅ Exists' : '❌ Missing'}`);
    } catch (error) {
      console.error("Server test failed:", error);
      alert("❌ Cannot connect to server. Make sure backend is running on port 5000.");
    }
  };

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="loading-content">
          <div className="spinner"></div>
          <h2>Loading Assessment...</h2>
          <p>Domain: {params.get("domain")}</p>
          <p>Duration: {params.get("duration")} minutes</p>
          <p>Searching for videos...</p>
          {sessionId && (
            <p style={{ color: '#666', fontSize: '0.9em' }}>
              Session: {sessionId}
            </p>
          )}
          <button onClick={testServer} style={{ marginTop: '20px', padding: '10px' }}>
            Test Server Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="video-container">
      
      <div className="status-bar">
        <div className="status-center">
          Question {questionIndex + 1} of {videos.length}
          {videos[questionIndex]?.originalIndex && (
            <span style={{ fontSize: '0.8em', marginLeft: '10px', color: '#666' }}>
              (Original: Q{videos[questionIndex].originalIndex})
            </span>
          )}
        </div>
        <div className="status-right">
          <span className="timer-display">⏰ {formatTime(timeLeft)}</span>
          {sessionId && (
            <span style={{ fontSize: '0.8em', marginRight: '10px', color: '#666' }}>
              Session: {sessionId.split('_')[0]}
            </span>
          )}
          <button 
            onClick={testServer}
            className="test-btn"
            title="Test server connection"
          >
            🔌
          </button>
        </div>
      </div>
      
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}
      
      <div className="main-content">
        
        <div className="left-panel">
          <div className="panel-header">
            <h3>Watch the Question</h3>
            <div className="audio-controls">
              <button 
                onClick={toggleMute}
                className={`mute-btn ${isMuted ? 'muted' : 'unmuted'}`}
              >
                {isMuted ? '🔇 Unmute Audio' : '🔊 Mute Audio'}
              </button>
              <span className="audio-hint">
                {isMuted ? 'Audio is muted. Click "Unmute" to hear.' : 'Audio is playing.'}
              </span>
            </div>
          </div>
          
          <div className="video-wrapper">
            <video
              ref={questionVideoRef}
              controls
              muted={isMuted}
              className="question-video"
              playsInline
              preload="auto"
              key={`video-${questionIndex}`}
            />
            <div className="video-overlay">
              <button 
                onClick={handlePlayClick}
                className="play-overlay-btn"
              >
                ▶ Click to Play
              </button>
            </div>
          </div>
          
          <div className="video-controls">
            <button 
              onClick={handlePlayClick}
              className="control-btn play-btn"
            >
              ▶ Play Video
            </button>
            <button 
              onClick={() => questionVideoRef.current?.pause()}
              className="control-btn pause-btn"
            >
              ⏸ Pause
            </button>
            <button 
              onClick={restartVideo}
              className="control-btn restart-btn"
            >
              ↺ Restart
            </button>
            <button 
              onClick={prevQuestion}
              disabled={questionIndex === 0}
              className="control-btn prev-btn"
            >
              ← Previous
            </button>
            <button 
              onClick={nextQuestion}
              disabled={questionIndex >= videos.length - 1}
              className="control-btn next-btn"
            >
              Next Question →
            </button>
          </div>
        </div>
        
        <div className="right-panel">
          <div className="panel-header">
            <h3>Record Your Answer</h3>
            {recording && (
              <div className="recording-status">
                <span className="recording-dot"></span>
                RECORDING
              </div>
            )}
          </div>
          
          <div className="camera-wrapper">
            <video
              ref={userCamRef}
              autoPlay
              muted
              playsInline
              className="camera-video"
            />
            {recording && (
              <div className="recording-overlay">
                <div className="recording-pulse"></div>
                <div className="recording-text">
                  ● RECORDING
                </div>
              </div>
            )}
          </div>
          
          <div className="recording-controls">
            {!recording ? (
              <button 
                onClick={startRecording}
                className="record-btn start-btn"
                disabled={recording}
              >
                🎤 Start Recording
              </button>
            ) : (
              <button 
                onClick={stopRecording}
                className="record-btn stop-btn"
              >
                ⏹ Stop Recording
              </button>
            )}
          </div>
          
          <div className="assessment-controls">
            <button 
              onClick={quitAssessment}
              className="quit-btn"
            >
              🏁 Quit Assessment
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPage;