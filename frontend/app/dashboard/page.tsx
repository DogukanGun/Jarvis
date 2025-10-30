'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { 
  Sparkles, 
  Terminal,
  Code2,
  DollarSign,
  FileText,
  GitBranch,
  Package,
  Globe,
  Mic,
  Send,
  Paperclip,
  X
} from "lucide-react";

export default function DashboardPage() {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'agent'; content: string }>>([]);
  const [voiceError, setVoiceError] = useState<string>('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  // Store transcript in ref for immediate access (no async state delays)
  const transcriptRef = useRef<string>('');

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
          recognitionRef.current = null;
        } catch (e) {
          console.error('Error stopping recognition on unmount:', e);
        }
      }
    };
  }, []);

  const handleSendMessage = () => {
    if (!inputText.trim() && attachedFiles.length === 0) return;
    
    setMessages([...messages, { role: 'user', content: inputText }]);
    setInputText('');
    setAttachedFiles([]);
    
    // Simulate agent response (replace with actual API call)
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'agent', 
        content: 'I\'m processing your request. This is where the agent response would appear with tool executions and results.' 
      }]);
    }, 1000);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const newFiles = Array.from(files);
      setAttachedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleVoiceInput = async () => {
    if (!isRecording) {
      // Start recording
      setIsRecording(true);
      transcriptRef.current = ''; // Reset transcript
      
      // Check for browser support
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Voice input is not supported in your browser. Please use Chrome or Edge.');
        setIsRecording(false);
        return;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognitionRef.current = recognition;
      
      recognition.continuous = true; // Keep listening
      recognition.interimResults = true; // Get interim results
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 1;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        let finalTranscript = '';
        let interimTranscript = '';
        
        // Process all results to get both final and interim transcripts
        for (let i = 0; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }
        
        // Store final results in ref for immediate access when stopping
        if (finalTranscript) {
          transcriptRef.current += finalTranscript;
        }
        
        // Update input with both final and interim results
        setInputText(transcriptRef.current + interimTranscript);
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        
        // Handle specific errors
        if (event.error === 'no-speech') {
          console.log('No speech detected, continuing to listen...');
          return;
        }
        
        if (event.error === 'network') {
          console.log('Network error, attempting to restart...');
          setVoiceError('Connection issue. Retrying...');
          
          // Clear error message after 3 seconds
          setTimeout(() => setVoiceError(''), 3000);
          
          // Try to restart after a brief delay
          setTimeout(() => {
            if (isRecording && recognitionRef.current) {
              try {
                recognitionRef.current.start();
              } catch (e) {
                console.error('Failed to restart after network error:', e);
                setVoiceError('Voice input failed. Please try again.');
                setTimeout(() => setVoiceError(''), 3000);
                setIsRecording(false);
                recognitionRef.current = null;
              }
            }
          }, 1000);
          return;
        }
        
        if (event.error === 'aborted') {
          console.log('Recognition aborted by user');
          setIsRecording(false);
          recognitionRef.current = null;
          return;
        }
        
        if (event.error === 'not-allowed') {
          setVoiceError('Microphone access denied. Please enable it in browser settings.');
          setTimeout(() => setVoiceError(''), 5000);
          setIsRecording(false);
          recognitionRef.current = null;
          return;
        }
        
        // For other errors, show message and stop recording
        console.error('Stopping recognition due to error:', event.error);
        setVoiceError(`Voice input error: ${event.error}`);
        setTimeout(() => setVoiceError(''), 3000);
        setIsRecording(false);
        recognitionRef.current = null;
      };

      recognition.onend = () => {
        // Only stop if user clicked stop, otherwise restart
        if (isRecording && recognitionRef.current) {
          try {
            recognition.start();
          } catch (e) {
            console.error('Failed to restart recognition:', e);
            setIsRecording(false);
            recognitionRef.current = null;
          }
        }
      };

      try {
        recognition.start();
      } catch (e) {
        console.error('Failed to start recognition:', e);
        setIsRecording(false);
        recognitionRef.current = null;
      }
    } else {
      // Stop recording
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      setIsRecording(false);
      
      // Print the final transcript to console (using ref for immediate access)
      console.log('=== VOICE INPUT CAPTURED ===');
      console.log('User said:', transcriptRef.current);
      console.log('Length:', transcriptRef.current.length, 'characters');
      console.log('===========================');
      
      // Update state with final transcript (trimmed)
      setInputText(transcriptRef.current.trim());
    }
  };

  return (
    <>
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto h-full flex flex-col">
            {messages.length === 0 ? (
              /* Empty State */
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-2xl">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-2xl mb-6 mx-auto">
                    <Sparkles className="w-10 h-10 text-white" />
                  </div>
                  <h1 className="text-4xl font-bold mb-3">Welcome to Jarvis</h1>
                  <p className="text-white/60 text-lg mb-8">
                    Your AI-powered development agent on Bitcoin L2. Start a conversation using text or voice.
                  </p>
                  
                  {/* Suggested Prompts */}
                  <div className="flex flex-wrap justify-center gap-3 mb-12">
                    <PromptCard 
                      icon={<Code2 className="w-4 h-4" />}
                      text="Create & deploy smart contract"
                      onClick={() => setInputText("Create a liquidity pool smart contract and deploy it to Mezo testnet")}
                    />
                    <PromptCard 
                      icon={<Terminal className="w-4 h-4" />}
                      text="Run Python data analysis"
                      onClick={() => setInputText("Run a Python script to analyze blockchain transaction data")}
                    />
                    <PromptCard 
                      icon={<GitBranch className="w-4 h-4" />}
                      text="Commit code & create PR"
                      onClick={() => setInputText("Commit my latest changes and create a pull request")}
                    />
                    <PromptCard 
                      icon={<Globe className="w-4 h-4" />}
                      text="Research DeFi protocols"
                      onClick={() => setInputText("Research the top DeFi protocols on Bitcoin L2")}
                    />
                    <PromptCard 
                      icon={<Package className="w-4 h-4" />}
                      text="Install dependencies"
                      onClick={() => setInputText("Install the required dependencies for a Solidity project")}
                    />
                    <PromptCard 
                      icon={<FileText className="w-4 h-4" />}
                      text="Read & analyze files"
                      onClick={() => setInputText("Read all smart contract files and suggest optimizations")}
                    />
                  </div>

                </div>
              </div>
            ) : (
              /* Messages */
              <div className="space-y-6 pb-6">
                {messages.map((message, idx) => (
                  message.role === 'user' ? (
                    <UserMessage key={idx} text={message.content} />
                  ) : (
                    <AgentMessage key={idx}>
                      <p>{message.content}</p>
                    </AgentMessage>
                  )
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-white/10 bg-[#1e1b4b]/50 backdrop-blur-sm p-4">
          <div className="max-w-4xl mx-auto">
            {/* Attached Files Display */}
            {attachedFiles.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {attachedFiles.map((file, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-2 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm"
                  >
                    <FileText className="w-4 h-4 text-[#F7931A]" />
                    <span className="text-white/80 max-w-[200px] truncate">{file.name}</span>
                    <span className="text-white/40 text-xs">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                    <button
                      onClick={() => removeFile(index)}
                      className="ml-2 p-1 hover:bg-white/10 rounded transition-colors"
                    >
                      <X className="w-3 h-3 text-white/60 hover:text-white" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Hidden File Input */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
              accept=".txt,.pdf,.doc,.docx,.json,.js,.ts,.py,.sol,.md"
            />

            <div className="relative">
              <textarea 
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={isRecording ? "Listening..." : "Message Jarvis... (press Enter to send, Shift+Enter for new line)"}
                className={`w-full bg-white/5 border ${isRecording ? 'border-red-500/50' : 'border-white/10'} rounded-lg px-4 py-3 pr-12 text-white placeholder:text-white/40 resize-none focus:outline-none focus:border-[#F7931A]/50 transition-colors`}
                rows={3}
                disabled={isRecording}
              />
              
              {/* Voice Input Button */}
              <button
                onClick={handleVoiceInput}
                className={`absolute right-3 top-3 p-2 rounded-lg transition-all ${
                  isRecording 
                    ? 'bg-red-500 text-white animate-pulse' 
                    : 'bg-white/10 hover:bg-white/20 text-white/60 hover:text-white'
                }`}
                title={isRecording ? "Stop recording" : "Start voice input"}
              >
                <Mic className="w-5 h-5" />
              </button>
              
              <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-xs text-white/60">
                    <DollarSign className="w-3 h-3" />
                    <span>Estimated cost: ~0.01 MEZO</span>
                  </div>
                  
                  {isRecording && (
                    <div className="flex items-center gap-2 text-xs text-red-400">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span>Recording...</span>
                    </div>
                  )}
                  
                  {voiceError && (
                    <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 rounded px-2 py-1">
                      <span>⚠️ {voiceError}</span>
                    </div>
                  )}
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setInputText('')}
                    className="text-xs text-white/40 hover:text-white/60 transition-colors px-3 py-1.5"
                  >
                    Clear
                  </button>
                  
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={handleAttachClick}
                    className="bg-transparent border-white/20 hover:bg-white/10 text-xs h-8"
                  >
                    <Paperclip className="w-3 h-3 mr-1.5" />
                    Attach
                  </Button>
                  
                  <Button 
                    size="sm"
                    onClick={handleSendMessage}
                    disabled={(!inputText.trim() && attachedFiles.length === 0) || isRecording}
                    className="bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white disabled:opacity-50 disabled:cursor-not-allowed h-8"
                  >
                    <Send className="w-3 h-3 mr-1.5" />
                    Send
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

function PromptCard({ icon, text, onClick }: { icon: React.ReactNode; text: string; onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className="inline-flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#F7931A]/30 rounded-lg px-4 py-2 transition-all"
    >
      <div className="text-[#FCD34D]">{icon}</div>
      <span className="text-sm text-white/80">{text}</span>
    </button>
  );
}

function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="bg-linear-to-br from-[#6B46C1]/30 to-[#3B82F6]/30 backdrop-blur-sm border border-[#6B46C1]/20 rounded-2xl px-6 py-4 max-w-2xl">
        <p className="text-white">{text}</p>
      </div>
    </div>
  );
}

function AgentMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className="shrink-0 w-10 h-10 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-lg flex items-center justify-center">
        <Sparkles className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl px-6 py-4">
        {children}
      </div>
    </div>
  );
}


