import { useState } from "react";
import "./App.css";
import About from "./About";
 
function DropZone() {
    const [dragging, setDragging] = useState(false);
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [prediction, setPrediction] = useState(null);
    const [error, setError] = useState("");
 
    const handleDragOver = (e) => {
        e.preventDefault();
        setDragging(true);
    };
 
    const handleDragLeave = () => setDragging(false);
 
    const handleDrop = (e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files[0];
 
        if (dropped) {
            setFile(dropped);
            setPrediction(null);
            setError("");
        }
    };
 
    const handleFileInput = (e) => {
        const selected = e.target.files[0];
 
        if (selected) {
            setFile(selected);
            setPrediction(null);
            setError("");
        }
    };
 
    const handleAnalyze = async () => {
        if (!file) return;
 
        setLoading(true);
        setError("");
        setPrediction(null);
 
        const formData = new FormData();
        formData.append("file", file);
 
        try {
            const response = await fetch("https://fmi-code-2026.onrender.com/predict", {
                method: "POST",
                body: formData,
            });
 
            const payload = await response.json().catch(() => ({}));
            console.log("API response:", payload);  // add this
            setPrediction(payload);
            
 
            if (!response.ok) {
                throw new Error(payload.detail || "Upload failed. Please try again.");
            }
 
            setPrediction(payload);
        } catch (requestError) {
            setError(requestError.message || "Unable to reach backend.");
        } finally {
            setLoading(false);
        }
    };
 
    return (
        <>
            <div
                className={`drop-zone ${dragging ? "drop-zone--active" : ""} ${file ? "drop-zone--filled" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <input
                    type="file"
                    accept=".wav,audio/wav"
                    id="file-input"
                    className="file-input"
                    onChange={handleFileInput}
                />
 
                {!file ? (
                    <>
                        <div className="drop-icon">
                            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <rect x="8" y="6" width="32" height="36" rx="4" strokeWidth="1.5" className="icon-rect" />
                                <path d="M24 18v12M18 24h12" strokeWidth="1.5" strokeLinecap="round" className="icon-plus" />
                                <path d="M16 36h16" strokeWidth="1.5" strokeLinecap="round" className="icon-line" />
                            </svg>
                        </div>
                        <p className="drop-label">Drop an audio file here</p>
                        <p className="drop-sub">WAV files only</p>
                        <label htmlFor="file-input" className="browse-btn">
                            Browse files
                        </label>
                    </>
                ) : (
                    <>
                        <div className="file-icon">
                            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <rect x="8" y="6" width="32" height="36" rx="4" strokeWidth="1.5" className="icon-rect" />
                                <path d="M18 26l4 4 8-8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="icon-check" />
                            </svg>
                        </div>
                        <p className="drop-label">{file.name}</p>
                        <p className="drop-sub">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                        <div className="analyze-actions">
                            <button className="browse-btn" onClick={handleAnalyze} disabled={loading}>
                                {loading ? "Analyzing..." : "Analyze file"}
                            </button>
                            <button
                                className="browse-btn"
                                onClick={() => {
                                    setFile(null);
                                    setPrediction(null);
                                    setError("");
                                }}
                                disabled={loading}
                            >
                                Remove
                            </button>
                        </div>
                    </>
                )}
            </div>
 
            {error && <p className="error-text">{error}</p>}
 

                

            {prediction && (
                <>
                    <section className="result-card">
                        <p className="result-title">Detection Result</p>
                        <p className={`result-status ${prediction.status === "ai" ? "result-status--ai" : "result-status--real"}`}>
                            {String(prediction.status || "unknown").toUpperCase()}
                        </p>
                        <p className="result-accuracy">
                            Confidence: {Math.round(Number(prediction.accuracy || 0) * 100)}%
                        </p>
                    </section>
 

                            {prediction.suspicious_parts && prediction.suspicious_parts.length > 0 && (() => {
    const totalDuration = Math.max(...prediction.suspicious_parts.map(p => p.end_sec));
    return (
        <div className="timeline-wrap">
            <div className="timeline-bar">
                {prediction.suspicious_parts.map((part, i) => {
                    const left = (part.start_sec / totalDuration) * 100;
                    const width = ((part.end_sec - part.start_sec) / totalDuration) * 100;
                    const alpha = part.score >= 0.75
                        ? 0.3 + (part.score - 0.75) / 0.25 * 0.7
                        : part.score / 0.75 * 0.15;
                    return (
                        <div
                            key={i}
                            className="timeline-segment"
                            style={{
                                left: `${left}%`,
                                width: `${width}%`,
                                background: `rgba(159, 45, 45, ${alpha})`,
                            }}
                            title={`${part.start_sec.toFixed(2)}s – ${part.end_sec.toFixed(2)}s · ${Math.round(part.score * 100)}% AI`}
                        />
                    );
                })}
            </div>
            <div className="timeline-labels">
                <span>0s</span>
                <span>{totalDuration.toFixed(2)}s</span>
            </div>
        </div>
    );
})()}




                    {prediction.suspicious_parts && prediction.suspicious_parts.length > 0 && (
                        <section className="suspicious-section">
                            <p className="suspicious-heading">Suspicious segments</p>
                            <p className="suspicious-sub">
                                The model flagged {prediction.suspicious_parts.length} segment{prediction.suspicious_parts.length > 1 ? "s" : ""} as likely AI-generated.
                            </p>
                            <div className="suspicious-list">
                                {prediction.suspicious_parts.map((part, i) => (
                                    <div key={i} className="suspicious-card">
                                        <div className="suspicious-card-header">
                                            <span className="suspicious-index">Segment {i + 1}</span>
                                            <span className="suspicious-time">
                                                {part.start_sec.toFixed(2)}s – {part.end_sec.toFixed(2)}s
                                            </span>
                                            <span className="suspicious-score">
                                                Score: {Math.round(part.score * 100)}%
                                            </span>
                                        </div>
                                        <div className="suspicious-images">
                                            <div className="suspicious-image-wrap">
                                                <p className="suspicious-image-label">Mel Spectrogram</p>
                                                <img
                                                    src={`https://fmi-code-2026.onrender.com${part.mel_image_url}`}
                                                    alt={`Mel spectrogram segment ${i + 1}`}
                                                    className="suspicious-img"
                                                />
                                            </div>
                                            <div className="suspicious-image-wrap">
                                                <p className="suspicious-image-label">MFCC</p>
                                                <img
                                                    src={`https://fmi-code-2026.onrender.com${part.mfcc_image_url}`}
                                                    alt={`MFCC segment ${i + 1}`}
                                                    className="suspicious-img"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                </>
            )}
        </>
    );
}
 
export default function App() {
    const [currentPage, setCurrentPage] = useState("home");
 
    if (currentPage === "about") {
        return <About onBack={() => setCurrentPage("home")} />;
    }
 
    return (
        <div className="app">
            <header className="header">
                <div className="header-inner">
                    <div className="logo">
                        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" width="28" height="28">
                            <rect width="32" height="32" rx="8" className="logo-bg" />
                            <path d="M10 22V16M14 22V12M18 22V10M22 22V16" strokeWidth="1.8" strokeLinecap="round" className="logo-bars" />
                        </svg>
                        <span className="logo-text">AudioVerify</span>
                    </div>
                    <nav className="nav">
                        <a
                            href="#"
                            className={`nav-link ${currentPage === "home" ? "nav-link--active" : ""}`}
                            onClick={() => setCurrentPage("home")}
                        >
                            Analyze
                        </a>
                        <a
                            href="#"
                            className={`nav-link ${currentPage === "about" ? "nav-link--active" : ""}`}
                            onClick={() => setCurrentPage("about")}
                        >
                            About
                        </a>
                    </nav>
                </div>
            </header>
 
            <main className="main">
                <section className="hero">
                    <p className="hero-badge">AI Detection</p>
                    <h1 className="hero-title">Is this audio real?</h1>
                    <p className="hero-sub">
                        Upload an audio file and our model will tell you whether it was
                        generated by AI or recorded by a human.
                    </p>
                </section>
 
                <DropZone />
 
                <footer className="footer">
                    <p>© 2026 AudioVerify. All rights reserved.</p>
                    <p className="fmi-tag">Built with ❤️ for FMI Hackathon</p>
                </footer>
            </main>
        </div>
    );
}