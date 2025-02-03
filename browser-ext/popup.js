// Load saved settings when popup opens
document.addEventListener('DOMContentLoaded', function() {
    chrome.storage.sync.get(['apiUrl', 'bearerToken'], function(data) {
        if (data.apiUrl) {
            document.getElementById('apiUrl').value = data.apiUrl;
        }
        if (data.bearerToken) {
            document.getElementById('bearerToken').value = data.bearerToken;
        }
    });
});

// Handle form submission
document.getElementById('settings-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const apiUrl = document.getElementById('apiUrl').value.trim();
    const bearerToken = document.getElementById('bearerToken').value.trim();
    
    // Validate inputs
    if (!apiUrl || !bearerToken) {
        showStatus('Please fill in all fields', false);
        return;
    }

    // Save to Chrome storage
    chrome.storage.sync.set({
        apiUrl: apiUrl,
        bearerToken: bearerToken
    }, function() {
        showStatus('Settings saved successfully!', true);
    });
});

function showStatus(message, isSuccess) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
    statusDiv.className = 'status ' + (isSuccess ? 'success' : 'error');
    
    // Hide status after 3 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}
