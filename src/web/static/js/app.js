/**
 * StreamRev Admin Panel JavaScript
 */

// Check authentication
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(endpoint, mergedOptions);
        
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        return null;
    }
}

// Logout function
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Check auth on page load
    checkAuth();
    
    // Add logout button if user is authenticated
    const token = localStorage.getItem('token');
    if (token) {
        const nav = document.querySelector('nav ul');
        if (nav) {
            const logoutLi = document.createElement('li');
            logoutLi.innerHTML = '<a href="#" onclick="logout()">Logout</a>';
            nav.appendChild(logoutLi);
        }
    }
});
