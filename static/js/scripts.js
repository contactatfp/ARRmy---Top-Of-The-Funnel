
document.querySelectorAll('[data-bs-target="#viewContactModal"]').forEach(function(button) {
    button.addEventListener('click', function() {
        // Fetch data or perform any other action required before showing the modal

        // Assuming account name is in the first column of the row that contains the clicked button
        document.getElementById('contactAccount').textContent = button.closest('tr').children[0].textContent;

        // This example sets static content, but you can replace this with dynamic content fetched from your server
    });
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


document.addEventListener("DOMContentLoaded", function(event) {

    // Variable to store the current Account ID
    let currentAccountId = null;

    // Capture the account ID when the menu button is clicked
    document.querySelectorAll(".open-contact-modal").forEach(button => {
        button.addEventListener("click", function() {
            currentAccountId = this.getAttribute("data-account-id");
        });
    });

    document.getElementById("logCallButton").addEventListener("click", function() {
        // Get the call subject and description from input fields
        const callSubject = document.getElementById("callSubject").value;
        const callDescription = document.getElementById("callDescription").value;
        const contactId = document.getElementById("contact").value;

        // Logic to log a call goes here.
        fetch("/logACall", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                contactId: contactId,
                subject: callSubject,
                description: callDescription,
                accountId: currentAccountId,

            }),
        })
            .then(response => {
                console.log("Response status: ", response.status);
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert("Call logged successfully");
                    // Hide the modal using Bootstrap's jQuery-based method
                    $('#viewContactModal').modal('hide');
                    // Reload the page to show the new account
                    location.reload();
                } else {
                    alert("Error logging call");
                    // Hide the modal
                    $('#viewContactModal').modal('hide');
                }
            });
    });
});

document.querySelectorAll('.open-contact-modal').forEach(function(button) {
    button.addEventListener('click', function(event) {
        var accountId = event.currentTarget.getAttribute('data-account-id');

        // Fetch the contacts for the selected account
        fetch('/getContacts?accountId=' + accountId)
            .then(response => response.json())
            .then(contacts => {
                // Populate the dropdown
                var select = document.getElementById('contact');
                select.innerHTML = '<option selected disabled value="">Select a Contact</option>';

                contacts.forEach(contact => {
                    var option = document.createElement('option');
                    option.value = contact.Id;
                    option.textContent = contact.Name;
                    select.appendChild(option);
                });
            });
    });
});


