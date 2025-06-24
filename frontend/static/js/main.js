// Multi-Agent System Frontend JavaScript

let isProcessing = false;

function updateStatus(message, type = 'normal') {
    const status = document.getElementById('agentStatus');
    status.innerHTML = `<span class="${type}">${message}</span>`;
}

function addMessageToChat(role, content, metadata = {}) {
    const chatHistory = document.getElementById('chatHistory');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    // Message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // NEW: Use .innerHTML to render HTML tags from the response
    contentDiv.innerHTML = content;

    messageDiv.appendChild(contentDiv);

    // Metadata for AI responses
    if (role === 'ai' && Object.keys(metadata).length > 0) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';

        let metaHTML = '';

        if (metadata.agent_used) {
            const agents = Array.isArray(metadata.agent_used) ? metadata.agent_used : [metadata.agent_used];
            metaHTML += agents.map(agent =>
                `<span class="agent-badge">${agent}</span>`
            ).join('');
        }

        if (metadata.classification) {
            metaHTML += `Classification: ${metadata.classification}`;
        }

        if (metadata.confidence !== undefined) {
            metaHTML += `<span class="confidence-score">Confidence: ${(metadata.confidence * 100).toFixed(1)}%</span>`;
        }

        if (metadata.execution_time !== undefined) {
            metaHTML += ` • ${metadata.execution_time}ms`;
        }

        metaDiv.innerHTML = metaHTML;
        messageDiv.appendChild(metaDiv);
    }

    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const agentSelect = document.getElementById('agentSelect');
    const includeReasoning = document.getElementById('includeReasoning');

    const message = userInput.value.trim();

    if (!message || isProcessing) return;

    // Update UI
    isProcessing = true;
    sendButton.disabled = true;
    sendButton.textContent = 'Processing...';
    updateStatus('Processing your request...', 'loading');

    // Add user message to chat
    addMessageToChat('user', message);
    userInput.value = '';

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                agent_type: agentSelect.value,
                include_reasoning: includeReasoning.checked
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        // Display bot response
        const botMessageElement = document.createElement('div');
        botMessageElement.classList.add('message', 'bot-message');

        // Render the response as HTML
        botMessageElement.innerHTML = data.response;

        chatHistory.appendChild(botMessageElement);

        // Scroll to the bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;

        updateStatus('Ready');

    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('ai', `Sorry, there was an error processing your request: ${error.message}`);
        updateStatus('Error occurred', 'error');
    } finally {
        // Reset UI
        isProcessing = false;
        sendButton.disabled = false;
        sendButton.textContent = 'Send';
        userInput.focus();
    }
}

// Handle Enter key
document.getElementById('userInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Load available agents on page load
document.addEventListener('DOMContentLoaded', async function () {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();

        console.log('Available agents:', data.agents);
        updateStatus('Ready');

        // You could populate agent descriptions here if needed

    } catch (error) {
        console.error('Failed to load agents:', error);
        updateStatus('Failed to load agents', 'error');
    }
});

// Agent selection change handler
document.getElementById('agentSelect').addEventListener('change', function (e) {
    const selectedAgent = e.target.value;
    updateStatus(`Selected: ${e.target.options[e.target.selectedIndex].text}`);
}); 