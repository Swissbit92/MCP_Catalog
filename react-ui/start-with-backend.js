#!/usr/bin/env node

// start-with-backend.js
// Script to start both FastAPI backend and React dev server
// Similar to run.py but for React development

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Load environment variables from .env if it exists
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const ROOT_DIR = path.join(__dirname, '..');
const SRC_DIR = path.join(ROOT_DIR, 'src');

console.log('🚀 Starting MCP Catalog with React UI...');

// Required environment variables
const requiredEnvVars = ['OLLAMA_BASE', 'PERSONA_MODEL'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`❌ Missing required environment variable: ${envVar}`);
    console.error(`   Set it in your .env file (e.g. ${envVar}=value)`);
    process.exit(1);
  }
}

// Check if Ollama is available and model is pulled
async function checkOllama() {
  const ollamaBase = process.env.OLLAMA_BASE || 'http://localhost:11434';
  const model = process.env.PERSONA_MODEL;

  try {
    const response = await fetch(`${ollamaBase}/api/tags`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    const models = data.models || [];
    const modelExists = models.some(m => m.name === model);

    if (!modelExists) {
      console.error(`❌ Ollama model '${model}' is not available.`);
      console.error(`   Available models: ${models.map(m => m.name).join(', ') || 'none'}`);
      console.error(`   👉 Pull the model first: ollama pull ${model}`);
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Could not contact Ollama. Is it running?');
    console.error(`   Base URL: ${ollamaBase}`);
    console.error(`   Error: ${error.message}`);
    console.error('   👉 Start Ollama app or run the daemon, then try again.');
    process.exit(1);
  }
}

// Start FastAPI backend
function startBackend() {
  console.log('🔧 Starting FastAPI backend...');

  const backendProcess = spawn('python', ['-m', 'uvicorn', 'src.coordinator.server:app', '--reload', '--port', '8000'], {
    cwd: ROOT_DIR,
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[BACKEND] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[BACKEND ERR] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (error) => {
    console.error('❌ Failed to start FastAPI backend:', error);
    process.exit(1);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
  });

  return backendProcess;
}

// Start React dev server
function startReact() {
  console.log('⚛️ Starting React dev server...');

  const reactProcess = spawn('npm', ['run', 'start:dev'], {
    cwd: __dirname,
    stdio: ['inherit', 'inherit', 'inherit'],
    shell: true
  });

  reactProcess.on('error', (error) => {
    console.error('❌ Failed to start React dev server:', error);
    process.exit(1);
  });

  return reactProcess;
}

// Main function
async function main() {
  try {
    // Check Ollama first
    await checkOllama();

    // Start backend
    const backendProcess = startBackend();

    // Wait for backend to start
    console.log('⏳ Waiting for backend to initialize...');
    await new Promise(resolve => setTimeout(resolve, 8000));

    // Test if backend is responding
    console.log('🔍 Testing backend connectivity...');
    try {
      const response = await fetch('http://127.0.0.1:8000/health');
      if (response.ok) {
        console.log('✅ Backend is responding');
      } else {
        console.log('⚠️ Backend responded with status:', response.status);
      }
    } catch (error) {
      console.log('❌ Backend not responding:', error.message);
      console.log('Continuing anyway...');
    }

    // Start React dev server
    const reactProcess = startReact();

    // Handle process termination
    const cleanup = () => {
      console.log('\n🛑 Shutting down...');
      try {
        backendProcess.kill();
      } catch (e) {
        // Ignore
      }
      try {
        reactProcess.kill();
      } catch (e) {
        // Ignore
      }
      process.exit(0);
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    // Wait for either process to exit
    await Promise.race([
      new Promise((resolve) => backendProcess.on('close', resolve)),
      new Promise((resolve) => reactProcess.on('close', resolve))
    ]);

    cleanup();

  } catch (error) {
    console.error('❌ Startup failed:', error);
    process.exit(1);
  }
}

main();