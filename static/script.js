$(document).ready(function () {
    // Only initialize DataTables if the library is loaded and the element exists
    if (typeof $.fn.DataTable !== 'undefined' && $('#leaderboard').length) {
        $('#leaderboard').DataTable({
            "pageLength": 10, // Default number of rows
            "lengthMenu": [ [10, 25, 50, -1], [10, 25, 50, "All"] ] // Rows per page options
        });
    }

    // Initialize DataTables for the team leaderboard
    if (typeof $.fn.DataTable !== 'undefined' && $('#teamLeaderboard').length) {
        $('#teamLeaderboard').DataTable({
            "pageLength": 10, // Default number of rows
            "lengthMenu": [ [10, 25, 50, -1], [10, 25, 50, "All"] ] // Rows per page options
        });
    }

    // Function to populate the team dropdown
    async function populateTeamDropdown() {
        try {
            const response = await fetch('/get_teams');
            const teams = await response.json();
            const teamSelect = document.getElementById('teamName');
            
            if (teamSelect) {
                // Clear existing options except the first one
                teamSelect.innerHTML = '<option value="" disabled selected>Select a team</option>';
                
                // Add teams to dropdown
                teams.forEach(teamName => {
                    const option = document.createElement('option');
                    option.value = teamName;
                    option.textContent = teamName;
                    teamSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error fetching teams:', error);
        }
    }

    // Initialize team dropdown on page load (only if it exists)
    if (document.getElementById('teamName')) {
        populateTeamDropdown();
    }

    // Handler for the Create Team form
    const createTeamForm = document.getElementById('createTeamForm');
    if (createTeamForm) {
        console.log('Create team form found, adding event listener');
        createTeamForm.addEventListener('submit', async function(event) {
            console.log('Form submission intercepted');
            event.preventDefault(); // Prevent default form submission
            
            const teamNameInput = document.getElementById('teamNameCreate');
            if (!teamNameInput) {
                console.error('Team name input not found');
                return;
            }
            
            const teamName = teamNameInput.value.trim();
            const responseMessage = document.getElementById('responseMessage');
            
            if (!teamName) {
                responseMessage.style.color = 'red';
                responseMessage.textContent = 'Please enter a team name.';
                return;
            }
            
            console.log('Submitting team:', teamName);

            try {
                const response = await fetch('/create_team', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: teamName }),
                });

                const result = await response.json();
                console.log('Response received:', result);

                if (response.ok) {
                    responseMessage.style.color = 'green';
                    responseMessage.textContent = `Team '${result.name}' created successfully!`;
                    teamNameInput.value = ''; // Clear input
                    // Refresh the team dropdown if it exists (on users page)
                    if (typeof populateTeamDropdown === 'function' && document.getElementById('teamName')) {
                        populateTeamDropdown();
                    }
                } else {
                    responseMessage.style.color = 'red';
                    responseMessage.textContent = `Error: ${result.detail}`;
                }
            } catch (error) {
                responseMessage.style.color = 'red';
                responseMessage.textContent = 'An unexpected error occurred.';
                console.error('Error creating team:', error);
            }
        });
    } else {
        console.log('Create team form not found');
    }

    // Handler for the Assign User form
    const assignUserForm = document.getElementById('assignUserForm');
    if (assignUserForm) {
        // Logic for user table row selection
        $('#usersTable tbody').on('click', 'tr', function () {
            const username = $(this).data('username');
            $('#userName').val(username); // Populate the form's username input

            // Optional: Add a visual indicator for the selected row
            $(this).siblings().removeClass('selected-row');
            $(this).addClass('selected-row');
        });

        assignUserForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const userName = document.getElementById('userName').value;
            const teamName = document.getElementById('teamName').value;
            const responseMessage = document.getElementById('responseMessage');

            try {
                const response = await fetch('/assign_user_to_team', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ user_name: userName, team_name: teamName }),
                });

                const result = await response.json();

                if (response.ok) {
                    responseMessage.style.color = 'green';
                    responseMessage.textContent = `User '${result.user_name}' assigned to team '${result.team_name}' successfully!`;
                    // Optionally clear the form and reload the page to show the change in the table
                    setTimeout(() => { window.location.reload(); }, 1500);
                } else {
                    responseMessage.style.color = 'red';
                    responseMessage.textContent = `Error: ${result.detail}`;
                }
            } catch (error) {
                responseMessage.style.color = 'red';
                responseMessage.textContent = 'An unexpected error occurred.';
                console.error('Error assigning user:', error);
            }
        });
    }

    // Initialize DataTables for the users table
    if (typeof $.fn.DataTable !== 'undefined' && $('#usersTable').length) {
        $('#usersTable').DataTable();
    }
});
