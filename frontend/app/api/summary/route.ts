import { NextRequest } from 'next/server';

/**
 * API Route for handling text summarization requests
 * This is an Edge Function that proxies requests to an AI summarization service
 * and streams the response back to the client.
 */

export const runtime = 'edge';

// Instructions for the AI summarization
const INSTRUCTION = `Summarize the content keeping the original meaning and tone. 
                     Do not add any additional information or context that is not 
                     present in the original content.`;

// Type for the expected request body
interface SummarizeRequest {
  content: string;
}

// Type for the upstream API response
interface UpstreamResponse {
  chunk?: string;
  error?: string;
}

/**
 * Handles POST requests for text summarization
 * Validates input, forwards to AI service, and streams the response
 */
export async function POST(req: NextRequest) {
  try {
    // Parse and validate request body
    const body = await req.json() as Partial<SummarizeRequest>;
    
    if (!body?.content?.trim()) {
      return new Response(
        JSON.stringify({ error: 'No content provided' }), 
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Get the upstream URL from environment variables
    const upstreamUrl = process.env.SUMMARY_UPSTREAM_URL;
    if (!upstreamUrl) {
      throw new Error('Upstream URL not configured');
    }

    const url = `${upstreamUrl}/ai/generate`;

    // Prepare the request body for the AI service
    const upstreamBody = {
      model_type: 'completion',
      params: {
        content: body.content.trim(),
        instruction: INSTRUCTION,
      },
      stream: true,
    };

    const upstreamResponse = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(upstreamBody),
    });

    if (!upstreamResponse.ok) {
      const error = await upstreamResponse.text();
      console.error('Upstream error:', error);
      return new Response(
        JSON.stringify({ 
          error: 'Failed to generate summary',
          details: error 
        }), 
        { 
          status: upstreamResponse.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    if (!upstreamResponse.body) {
      return new Response(
        JSON.stringify({ error: 'No response body from upstream' }),
        { 
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Create a transform stream to process the SSE stream
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const reader = upstreamResponse.body.getReader();
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    /**
     * Processes the streaming response from the AI service
     * Handles Server-Sent Events (SSE) format and error states
     */
    const processStream = async () => {
      try {
        // Process the stream until completion
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // Decode and process the SSE stream
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(line => line.trim() !== '');
          
          for (const line of lines) {
            // Handle SSE data lines
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              
              // Check for stream end marker
              if (data === '[DONE]') {
                await writer.close();
                return;
              }
              
              try {
                const parsed: UpstreamResponse = JSON.parse(data);
                
                // Handle errors from upstream
                if (parsed.error) {
                  console.error('Error from upstream:', parsed.error);
                  await writer.write(encoder.encode(JSON.stringify(parsed)));
                  await writer.close();
                  return;
                }
                
                // Forward valid chunks to the client
                if (parsed.chunk) {
                  await writer.write(encoder.encode(parsed.chunk));
                }
              } catch (e) {
                console.error('Error parsing upstream data:', e);
                // Continue processing other lines if one fails
              }
            }
          }
        }
      } catch (error) {
        console.error('Stream processing error:', error);
        try {
          // Try to send error to client before closing
          await writer.write(encoder.encode(JSON.stringify({
            error: 'Error processing stream',
            details: error instanceof Error ? error.message : 'Unknown error'
          })));
        } catch (writeError) {
          console.error('Failed to write error to stream:', writeError);
        }
      } finally {
        try {
          // Ensure writer is always closed
          await writer.close();
        } catch (closeError) {
          console.error('Error closing writer:', closeError);
        }
      }
    };

    // Start processing the stream asynchronously
    processStream().catch(console.error);
    processStream();

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-cache',
        'Content-Encoding': 'none',
        'Transfer-Encoding': 'chunked',
      },
    });
  } catch (error) {
    console.error('Unexpected error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      }), 
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}