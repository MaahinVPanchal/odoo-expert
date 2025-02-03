function debug(msg, ...args) {
    console.log(`[Odoo Expert] ${msg}`, ...args);
}

// Main initialization function
function initializeAIResponse() {
    try {
        debug('Initializing AI response section');
        
        // Check if the AI response section already exists
        if (document.getElementById('ai-response-section')) {
            debug('AI response section already exists, skipping initialization');
            return;
        }
        
        // Create AI response section
        const aiSection = document.createElement('div');
        aiSection.id = 'ai-response-section';
        aiSection.innerHTML = `
            <h2>Odoo Expert Response</h2>
            <div id="ai-response-content">Initializing...</div>
        `;

        // Try to find the search results container
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            debug('Found search results container');
            searchResults.parentNode.insertBefore(aiSection, searchResults);
            processSearchQuery();
        } else {
            debug('Search results container not found');
        }
    } catch (error) {
        debug('Error during initialization:', error);
    }
}

function getVersionFromUrl() {
    const match = window.location.pathname.match(/\/documentation\/(\d+\.\d+)\//);
    if (match) {
        return parseInt(match[1]) * 10;
    }
    return 180; // default to version 18
}

async function fetchAIResponse(query, version, apiUrl, bearerToken) {
    const responseDiv = document.getElementById('ai-response-content');
    if (!responseDiv) {
        debug('Response div not found');
        return;
    }

    debug('Fetching AI response', { query, version });
    responseDiv.innerHTML = 'Loading response...';

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${bearerToken}`,
                'Origin': 'https://www.odoo.com'
            },
            body: JSON.stringify({ query, version }),
            mode: 'cors'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let result = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            result += decoder.decode(value, { stream: true });
            try {
                const htmlContent = marked.parse(result);
                responseDiv.innerHTML = htmlContent;
            } catch (e) {
                debug('Error parsing markdown:', e);
            }
        }
    } catch (error) {
        debug('Error fetching response:', error);
        if (error.message.includes('CORS')) {
            responseDiv.innerHTML = `
                <p>Error: CORS issue detected. Please update your API server to allow CORS requests:</p>
                <ol>
                    <li>Install the <code>fastapi-cors</code> package: <code>pip install fastapi-cors</code></li>
                    <li>Update your main.py file to include CORS middleware:</li>
                </ol>
                <pre>
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.odoo.com", "chrome-extension://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
                </pre>
                <p>After updating your API server, please refresh this page and try again.</p>
            `;
        } else {
            responseDiv.innerHTML = `Error fetching AI response: ${error.message}. Please verify your API settings in the extension popup.`;
        }
    }
}

function processSearchQuery() {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');

    if (!query) {
        debug('No search query found');
        return;
    }

    debug('Processing search query:', query);
    chrome.storage.sync.get(['apiUrl', 'bearerToken'], function(data) {
        debug('Got storage data:', { apiUrl: data.apiUrl, hasToken: !!data.bearerToken });
        if (!data.apiUrl || !data.bearerToken) {
            const responseDiv = document.getElementById('ai-response-content');
            if (responseDiv) {
                responseDiv.innerHTML = 'Please configure the API settings in the extension popup.';
            }
            return;
        }

        const version = getVersionFromUrl();
        fetchAIResponse(query, version, data.apiUrl, data.bearerToken);
    });
}

// Watch for dynamic page updates
const observer = new MutationObserver((mutations) => {
    if (!document.getElementById('ai-response-section')) {
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            debug('Search results found via observer');
            initializeAIResponse();
        }
    }
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Initial setup
debug('Content script starting', { url: window.location.href });
// Use requestAnimationFrame to ensure the DOM is fully loaded
requestAnimationFrame(() => {
    initializeAIResponse();
});

// Cleanup function to remove extra AI response sections
function cleanupExtraAIResponses() {
    const aiResponseSections = document.querySelectorAll('#ai-response-section');
    if (aiResponseSections.length > 1) {
        debug(`Found ${aiResponseSections.length} AI response sections, removing extras`);
        for (let i = 1; i < aiResponseSections.length; i++) {
            aiResponseSections[i].remove();
        }
    }
}

// Run cleanup after a short delay
setTimeout(cleanupExtraAIResponses, 1000);
