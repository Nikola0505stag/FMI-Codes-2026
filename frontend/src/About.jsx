import React from "react";
import "./App.css";

export default function About({ onBack }) {
  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo" onClick={onBack} style={{ cursor: "pointer" }}>
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" width="28" height="28">
              <rect width="32" height="32" rx="8" className="logo-bg" fill="#3b82f6"/>
              <path d="M10 22V16M14 22V12M18 22V10M22 22V16" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <span className="logo-text">AudioVerify</span>
          </div>
          <nav className="nav">
            <a href="#" className="nav-link" onClick={onBack}>Analyze</a>
            <a href="#" className="nav-link nav-link--active">About</a>
          </nav>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <p className="hero-badge">Our Mission</p>
          <h1 className="hero-title">About AudioVerify</h1>
          <p className="hero-sub">
            This project was built for the FMI Hackathon. Our goal is to fight 
            AI-generated misinformation by providing a tool that detects 
            synthetic audio with high accuracy.
          </p>

		<div className="how-it-works-container">
		  <h2 className="section-title">How it works</h2>
		  <div className="steps-grid">
			<div className="step-card">
			  <div className="step-num">01</div>
			  <h3>Upload Audio</h3>
			  <p>Select or drag and drop your MP3/WAV file into the secure analyzer zone.</p>
			</div>
			
			<div className="step-card">
			  <div className="step-num">02</div>
			  <h3>AI Processing</h3>
			  <p>Our deep learning model extracts features like mel-spectrograms to detect anomalies.</p>
			</div>
			
			<div className="step-card">
			  <div className="step-num">03</div>
			  <h3>Instant Report</h3>
			  <p>Get a probability score showing if the voice is human or AI-generated.</p>
			</div>
		  </div>
		</div>

      
      <div style={{ marginTop: '40px' }}>
        <button className="browse-btn" onClick={onBack}>
          Back to Analyzer
        </button>
      </div>

      <footer className="footer">
        <p>© 2026 AudioVerify. All rights reserved.</p>
        <p className="fmi-tag">Built with ❤️ for FMI Hackathon</p>
      </footer>

        </section>
      </main>
    </div>
  );
}
