import { NextRequest } from 'next/server';

export const runtime = 'edge';

const INSTRUCTION = `Summarize the content keeping the original meaning and tone. 
                     Do not add any additional information or context that is not 
                     present in the original content.`;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    if (!body.content) {
      return new Response(JSON.stringify({ error: 'No content provided' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const url = `${process.env.SUMMARY_UPSTREAM_URL}/ai/generate`;

    const upstreamBody = {
      model_type: 'completion',
      params: {
        content: body.content,
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

    // Process the stream
    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // Process the SSE stream
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(line => line.trim() !== '');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data === '[DONE]') {
                await writer.close();
                return;
              }
              
              try {
                const parsed = JSON.parse(data);
                if (parsed.error) {
                  console.error('Error from upstream:', parsed.error);
                  await writer.write(encoder.encode(JSON.stringify(parsed)));
                  await writer.close();
                  return;
                }
                
                // Forward the chunk as is
                await writer.write(encoder.encode(parsed.chunk));
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (e) {
        console.error('Stream error:', e);
        try {
          await writer.write(encoder.encode(JSON.stringify({ 
            error: 'Error processing stream',
            details: e instanceof Error ? e.message : String(e)
          })));
        } catch (writeError: unknown) {
          const error = writeError as Error;
          console.error('Failed to write error to stream:', error.message || String(writeError));
        }
      } finally {
        try {
          await writer.close();
        } catch (closeError: unknown) {
          const error = closeError as Error;
          // Ignore errors when closing an already closed writer
          if (error.name !== 'TypeError' || !error.message.includes('closed')) {
            console.error('Error closing writer:', error.message || String(closeError));
          }
        }
      }
    };

    // Start processing the stream
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