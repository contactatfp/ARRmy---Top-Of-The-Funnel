
    document.querySelector('[data-bs-target="#viewContactModal"]').addEventListener('click', function() {
    // Fetch data or perform any other action required before showing the modal

    // Example: set the contact name and account
    document.getElementById('contactName').textContent = 'Sample Contact Name';
    document.getElementById('contactAccount').textContent = 'Sample Account Name';

    // This example sets static content, but you can replace this with dynamic content fetched from your server
});




    document.getElementById("add-account-form").addEventListener("submit", function(event) {
    event.preventDefault();
    const name = document.getElementById("name").value;
    const street = document.getElementById("street").value;
    const city = document.getElementById("city").value;
    const state = document.getElementById("state").value;
    const zip = document.getElementById("zip").value;

    // Call add_account with the form values
    fetch("/add_account", {
    method: "POST",
    headers: {
    "Content-Type": "application/json",
},
    body: JSON.stringify({ name, street, city, state, zip }),
})
    .then(response => {
    console.log("Response status: ", response.status);
    return response.json();
})
    .then(data => {
    if (data.success) {
    alert("Account added successfully");
    // Hide the modal using Bootstrap's jQuery-based method
    $('#addAccountModal').modal('hide');
    // Reload the page to show the new account
    location.reload();
} else {
    alert("Error adding account");
}
})
    .catch(error => {
    console.error("Error fetching data: ", error);
    $('#addAccountModal').modal('hide');
});
});


    document.getElementById("logCallButton").addEventListener("click", function() {
        // Logic to log a call goes here.
        // This is just an example. You need to replace it with the actual logic for logging a call.
        alert("Log a call for: " + document.getElementById("contactName").textContent);

        // Hide the modal
        $('#viewContactModal').modal('hide');
    });
