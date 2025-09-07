let uploadedFilePath = "";

// Handle File Upload
function uploadFile() {
    const fileInput = document.getElementById("uploadFile");
    if (fileInput.files.length === 0) {
        alert("Please select a file");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.filepath) {
            uploadedFilePath = data.filepath;
            alert("File uploaded successfully!");
        } else {
            alert("Failed to upload file");
        }
    })
    .catch(error => console.error("Upload error:", error));
}

// Generate Report
function generateReport() {
    if (!uploadedFilePath) {
        alert("Please upload a file first");
        return;
    }

    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;

    fetch("/generate-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filepath: uploadedFilePath, start_date: startDate, end_date: endDate })
    })
    .then(response => response.json())
    .then(data => {
        if (data.report) {
            document.getElementById("reportContainer").innerText = data.report;
        } else {
            alert("No report generated");
        }
    })
    .catch(error => console.error("Report error:", error));
}

// Send Email
function sendEmail() {
    if (!uploadedFilePath) {
        alert("Please upload a file first");
        return;
    }

    fetch("/send-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filepath: uploadedFilePath })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    })
    .catch(error => console.error("Email error:", error));
}
