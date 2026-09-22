document.getElementById('excelFile').addEventListener('change', function(e) {
    const fileName = e.target.files[0]?.name || 'Select Excel File';
    document.getElementById('fileLabel').textContent = fileName;
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('excelFile');
    const dateTimeInput = document.getElementById('meetingDateTime');
    const durationInput = document.getElementById('meetingDuration');
    const errorBox = document.getElementById('errorBox');
    const submitBtn = document.getElementById('submitBtn');
    const loader = document.getElementById('loader');
    const resultsDiv = document.getElementById('results');
    const resultsList = document.getElementById('resultsList');

    errorBox.classList.add('hidden');
    errorBox.textContent = '';
    
    if (!dateTimeInput.value) {
        showError('Please select a meeting date and time.');
        return;
    }

    const file = fileInput.files[0];
    if (!file) {
        showError('Please select an Excel file (.xlsx or .xls).');
        return;
    }

    // Automatically detect current user timezone (e.g., "Asia/Kolkata")
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';

    const formData = new FormData();
    formData.append('file', file);
    formData.append('start_time', dateTimeInput.value); // Sends local "YYYY-MM-DDTHH:MM" directly
    formData.append('duration', durationInput.value);
    formData.append('timezone', userTimezone);

    submitBtn.disabled = true;
    loader.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    resultsList.innerHTML = '';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'An error occurred while creating the meeting.');
        }

        // Render the single shared Meet link and confirmation
        resultsList.innerHTML = `
            <li style="background: #e8f8f5; border: 1px solid #a3e4d7; padding: 15px; border-radius: 6px; margin-bottom: 15px; text-align: left;">
                <div style="font-size: 1.1em; font-weight: bold; color: #117a65; margin-bottom: 8px;">🎉 Workshop Scheduled Successfully!</div>
                <div style="margin-bottom: 5px;"><strong>📅 Scheduled Time:</strong> ${data.start_time} to ${data.end_time} (${data.timezone})</div>
                <div style="margin-bottom: 5px;"><strong>🔗 Shared Google Meet Link:</strong> <a href="${data.meet_link}" target="_blank" style="color: #2980b9; font-weight: bold; word-break: break-all;">${data.meet_link}</a></div>
                <div><strong>📩 Total Invitations Sent:</strong> ${data.invited_count} participant(s)</div>
            </li>
            <li style="font-weight: bold; padding: 5px 0; border-bottom: 2px solid #ccc;">Invited Recipients (All assigned to above Meet link):</li>
        `;

        data.emails.forEach(email => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="success">✓</span> ${email}`;
            resultsList.appendChild(li);
        });

        resultsDiv.classList.remove('hidden');
    } catch (error) {
        showError(error.message);
    } finally {
        submitBtn.disabled = false;
        loader.classList.add('hidden');
    }

    function showError(msg) {
        errorBox.textContent = msg;
        errorBox.classList.remove('hidden');
    }
});