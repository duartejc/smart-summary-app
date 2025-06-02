'use client';

import { useState, useEffect, useCallback } from 'react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Sparkles } from 'lucide-react';

import { cn } from '@/lib/utils';

/**
 * Main application component that provides a text summarization interface.
 * Features:
 * - Text input with word count
 * - AI-powered summarization
 * - Typewriter effect for summary display
 * - Responsive layout
 */
export default function Home() {
  // State for client-side rendering
  const [isClient, setIsClient] = useState(false);
  
  // Form and API state
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [content, setContent] = useState("");
  const [wordCount, setWordCount] = useState(0);
  const [activeTab, setActiveTab] = useState<'input' | 'summary'>('input');
  
  // Summary display state
  const [summary, setSummary] = useState('');
  const [fullSummary, setFullSummary] = useState(''); // Complete summary text
  const [displayedSummary, setDisplayedSummary] = useState(''); // Currently displayed portion
  const [isTyping, setIsTyping] = useState(false);
  const [showCursor, setShowCursor] = useState(true); // Cursor visibility for typewriter effect
  const [typingTimeout, setTypingTimeout] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Update word count when content changes
  useEffect(() => {
    const words = content.trim() ? content.trim().split(/\s+/).length : 0;
    setWordCount(words);
  }, [content]);

  /**
   * Controls the blinking cursor effect during typing
   * Only active when isTyping is true
   */
  useEffect(() => {
    if (!isTyping) {
      setShowCursor(false);
      return;
    }
    
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(cursorInterval);
  }, [isTyping]);
  
  // Typewriter effect for displaying the summary
  useEffect(() => {
    if (!isTyping) return;

    if (displayedSummary.length < fullSummary.length) {
      const timeout = setTimeout(() => {
        setDisplayedSummary(prev => fullSummary.substring(0, prev.length + 1));
      }, 20);
      
      setTypingTimeout(timeout);
      
      return () => {
        if (timeout) {
          clearTimeout(timeout);
        }
      };
    } else {
      setIsTyping(false);
    }
    
    return () => {
      if (typingTimeout) {
        clearTimeout(typingTimeout);
      }
    };
  }, [displayedSummary, fullSummary, isTyping, typingTimeout]);

  /**
   * Typewriter effect that reveals text character by character
   * Creates a smooth, animated typing effect for the summary
   */
  useEffect(() => {
    if (!fullSummary || fullSummary === displayedSummary) {
      setIsTyping(false);
      return;
    }

    setIsTyping(true);
    let currentIndex = 0;
    const typingSpeed = 20; // ms per character
    let timeoutId: NodeJS.Timeout;

    const typeCharacter = () => {
      if (currentIndex < fullSummary.length) {
        setDisplayedSummary(fullSummary.substring(0, currentIndex + 1));
        currentIndex++;
        timeoutId = setTimeout(typeCharacter, typingSpeed);
      } else {
        setIsTyping(false);
      }
    };

    // Start with a small delay to show the cursor first
    timeoutId = setTimeout(typeCharacter, 100);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [fullSummary]);

  /**
   * Processes incoming text chunks from the streaming response
   * Manages the full summary state and triggers the typewriter effect
   */
  const processStreamText = useCallback((text: string) => {
    setFullSummary(prev => {
      const newText = prev + text;
      // If we're not currently typing, reset the display to start new typing effect
      if (!isTyping) {
        setDisplayedSummary('');
        return newText;
      }
      return newText;
    });
  }, [isTyping]);

  /**
   * Handles the summarization process
   * 1. Validates input
   * 2. Makes API request to summarization service
   * 3. Processes the streaming response
   * 4. Manages loading states and errors
   */
  const handleSummarize = useCallback(async () => {
    if (isSummarizing || !content.trim()) return;
  
    // Reset states for new summary
    setIsSummarizing(true);
    setActiveTab('summary');
    setDisplayedSummary("");
    setFullSummary("");
    setSummary("");
    setIsTyping(true);
    
    let localSummary = "";
  
    try {
      // Make request to our API route
      const res = await fetch('/api/summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });
  
      // Handle non-OK responses
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.error || 'Failed to generate summary');
      }
  
      if (!res.body) throw new Error('No response body from server');
  
      // Set up streaming reader
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
  
      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
  
        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });
  
        // Process complete lines from the buffer
        let startIndex = 0;
        let endIndex;
  
        while ((endIndex = buffer.indexOf('\n', startIndex)) !== -1) {
          const line = buffer.slice(startIndex, endIndex).trim();
          startIndex = endIndex + 1;
  
          if (line) {
            processStreamText(line + '\n');
            // Small delay between chunks for better visibility
            await new Promise(resolve => setTimeout(resolve, 50));
          }
        }
  
        // Keep any incomplete data for next iteration
        buffer = buffer.slice(startIndex);
      }
  
      // Process any remaining data in buffer
      if (buffer.trim()) {
        localSummary += buffer.trim();
        processStreamText(buffer.trim());
      }
  
    } catch (error) {
      console.error('Error generating summary:', error);
      localSummary = `Error: ${error instanceof Error ? error.message : 'Failed to generate summary'}`;
      setFullSummary(localSummary);
      setDisplayedSummary(localSummary);
    } finally {
      setSummary(localSummary);
      setIsSummarizing(false);
    }
  }, [content, isSummarizing, processStreamText]);
  
  const isSummarizeDisabled = wordCount === 0 || isSummarizing;

  if (!isClient) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-center bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Smart Summary AI
          </h1>
          <p className="text-center text-muted-foreground mt-2">
            Transform your text into concise, meaningful summaries with AI
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0 h-[calc(100vh-160px)]">
          
          {/* Input Section */}
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-lg font-semibold">Your Text</h2>
              <div className="text-sm text-muted-foreground">
                {wordCount} {wordCount === 1 ? 'word' : 'words'}
              </div>
            </div>
            <div className="flex-1 flex overflow-y-auto flex-col border rounded-lg bg-white dark:bg-gray-900">
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste your text here to summarize..."
                  className="w-full min-h-[75vh] max-h-[75vh] resize-none overflow-y-auto h-auto !text-lg border-0 focus-visible:ring-0 bg-transparent !ring-0 !ring-offset-0 whitespace-pre-wrap"
                />
            </div>
            <div className="mt-4 flex justify-center">
              <Button 
                onClick={handleSummarize} 
                disabled={isSummarizeDisabled}
                className="w-full max-w-xs gap-2 transition-all duration-200 cursor-pointer overflow-auto"
                variant={isSummarizing ? "secondary" : "default"}
                size="lg"
              >
                {isSummarizing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Summarizing...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate Summary
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Summary Section */}
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-lg font-semibold">AI Summary</h2>
              <div className="text-sm text-muted-foreground">
                {activeTab === 'summary' && summary ? 'AI-generated summary' : 'Summary will appear here'}
              </div>
            </div>
            <div className={cn(
              "flex-1 flex flex-col border rounded-lg overflow-hidden bg-white dark:bg-gray-900 relative",
              !summary && "items-center justify-center"
            )}>
              {summary ? (
                <div className="flex-1 flex flex-col relative overflow-hidden">
                  <div className="absolute inset-0 overflow-auto">
                    <Textarea
                      value={displayedSummary + (isTyping && showCursor ? "▍" : "")}
                      className="min-h-[65vh] max-h-[65vh] resize-none overflow-y-auto h-auto !text-lg border-0 focus-visible:ring-0 bg-transparent !ring-0 !ring-offset-0 whitespace-pre-wrap"
                      readOnly
                    />
                  </div>
                </div>
              ) : (
                <div className={`text-center p-8 text-muted-foreground ${isSummarizing ? "animate-pulse" : ""}`}>
                  <Sparkles className="mx-auto h-12 w-12 mb-4 text-gray-300" />
                  <p>Your AI-generated summary will appear here</p>
                  <p className="text-sm mt-2">Enter some text and click &quot;Generate Summary&quot;</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-4 mt-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>Jean Duarte © {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}
