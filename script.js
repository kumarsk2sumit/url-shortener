const API_URL = 'https://t3kpvfmsa4.execute-api.ap-southeast-1.amazonaws.com/prod';

async function shortenURL() {
    const longURL = document.getElementById('longURL').value.trim();

    if (!longURL) {
        showError('Please enter a URL first.');
        return;
    }

    if (!longURL.startsWith('http://') && !longURL.startsWith('https://')) {
        showError('URL must start with http:// or https://');
        return;
    }

    const btn = document.getElementById('shortenBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');

    btnText.classList.add('hidden');
    btnLoader.classList.remove('hidden');
    btn.disabled = true;

    hideError();
    hideResult();

    try {
        const response = await fetch(`${API_URL}/shorten`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: longURL })
        });

        const data = await response.json();

        if (response.ok) {
            showResult(data.shortURL);
        } else {
            showError(data.error || 'Something went wrong. Please try again.');
        }

    } catch (err) {
        showError('Could not connect to the server. Check your internet connection.');
        console.error(err);
    }

    btnText.classList.remove('hidden');
    btnLoader.classList.add('hidden');
    btn.disabled = false;
}

async function copyURL() {
    const shortURL = document.getElementById('shortURLDisplay').value;
    const copyText = document.getElementById('copyText');

    try {
        await navigator.clipboard.writeText(shortURL);

        copyText.textContent = 'Copied!';
        document.getElementById('copyConfirm').classList.remove('hidden');

        setTimeout(() => {
            copyText.textContent = 'Copy';
            document.getElementById('copyConfirm').classList.add('hidden');
        }, 2000);

    } catch (err) {
        const input = document.getElementById('shortURLDisplay');
        input.select();
        document.execCommand('copy');
        copyText.textContent = 'Copied!';
        setTimeout(() => { copyText.textContent = 'Copy'; }, 2000);
    }
}

function showResult(shortURL) {
    document.getElementById('shortURLDisplay').value = shortURL;
    document.getElementById('resultBox').classList.remove('hidden');
}

function hideResult() {
    document.getElementById('resultBox').classList.add('hidden');
}

function showError(message) {
    const el = document.getElementById('errorMsg');
    el.textContent = message;
    el.classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorMsg').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('longURL').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            shortenURL();
        }
    });
});