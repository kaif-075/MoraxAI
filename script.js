const btnn = document.getElementById('btnn');


    loadProfile();
    async function loadProfile(){
 try{

    const response = await fetch(
      "http://127.0.0.1:5000/profile",
      {
        credentials:"include"
      }
    );

    const data = await response.json();

    if(data.success){

      document.getElementById('header').innerText =
        "Welcome, " + data.name;

      document.getElementById('studentName').innerText =
        data.name;

      document.getElementById('studentPin').innerText =
        data.pin;

      document.getElementById('studentBranch').innerText =
        data.branch;

        document.getElementById('studentSemester').innerText =
        data.semester;

      document.getElementById('studentAttendance').innerText =
        data.attendance + "%";
    }

    else{
      window.location.href = "login.html";
    }

  }
  catch(err){
    console.log(err);
  }
    }
    
    const inputbar = document.getElementById('inputbar');
    const chatContainer = document.getElementById('chatContainer');
    
    inputbar.addEventListener('input', () =>{
      inputbar.style.height = 'auto';
      inputbar.style.height=inputbar.scrollHeight + 'px';
    });

    btnn.addEventListener('click',sendMessage);
    inputbar.addEventListener('keydown',function(e){
      if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        sendMessage();
      }
    });
     async function logoutStudent() {
      await fetch("http://127.0.0.1:5000/logout",{
        method:"POST",
        credentials:"include"
      });
      window.location.href="login.html";
      
    }
    function createTimeTable(title, rows){

    let html = `<h3>${title}</h3>`;

    html += `
    <table class="marks-table">
        <tr>
            <th>Day</th>
            <th>P1</th>
            <th>P2</th>
            <th>P3</th>
            <th>P4</th>
            <th>P5</th>
            <th>P6</th>
            <th>P7</th>
        </tr>
    `;

    // Group by day
    const timetable = {};

    rows.forEach(row => {

        if(!timetable[row.day_name]){
            timetable[row.day_name] = {};
        }

        timetable[row.day_name][row.period_no] = row.subject;

    });

    // Create rows
    for(let day in timetable){

        html += `
        <tr>
            <td>${day}</td>
            <td>${timetable[day][1] || "-"}</td>
            <td>${timetable[day][2] || "-"}</td>
            <td>${timetable[day][3] || "-"}</td>
            <td>${timetable[day][4] || "-"}</td>
            <td>${timetable[day][5] || "-"}</td>
            <td>${timetable[day][6] || "-"}</td>
            <td>${timetable[day][7] || "-"}</td>
        </tr>
        `;
    }

    html += `</table>`;

    return html;
}
 
      async function sendMessage(){
      document.getElementById('header').style.display = 'none';
      const userText = inputbar.value.trim();
      if(userText == '') return;
      appendMessage(userText,'user');
      const typingMessage = appendMessage("Bot is Thinking....","bot");
      inputbar.value='';
  

 

      try{

    const response = await fetch(
        "http://127.0.0.1:5000/chat",
        {

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },
            credentials:"include",
            body:JSON.stringify({
                message:userText
            })
        }
    );
    const data = await response.json();
    console.log(data);
    if (data.url){
      typingMessage.innerHTML = `${data.reply} <a href="${data.url}" target="_blank">${data.link_text}</a>`;
      return;
    
    }
    if(data.type === "timetable"){
    typingMessage.innerHTML =
        createTimeTable(data.title,data.data);
        return;
    
}
if(data.type === "sbtet_result"){

    typingMessage.innerHTML = `
        <h3>${data.title}</h3>

        <p><b>Name:</b>
        ${data.data.name}</p>
        <p><b>Branch:</b>
        ${data.data.branch}</p>

        <p><b>Grand Total:</b>
        ${data.data.grand_total}</p>

        <p><b>GPA:</b>
        ${data.data.gpa}</p>

        <p><b>Result:</b>
        ${data.data.result}</p>
    `;
        return;

}
if(data.type === "teachers"){
    typingMessage.innerHTML =
        createTeachersTable(data.title,data.data);
              return;
  
}
if(data.type==="today_classes"){
    typingMessage.innerHTML =
    createTodayClasses(data.title,data.data);
        return;

}
        if(data.type){
          typingMessage.innerHTML = createTable(data.title,data.data,data.type);
                return;

        }
      
    else{
    let reply = data.reply
    .replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank">$1</a>'
    )
    .replace(/\*\*(.*?)\*\*/g,'<b>$1</b>')
    .replace(/\n/g,'<br>');

typingMessage.innerHTML = reply;
    }

}
catch(err){

    typingMessage.innerHTML =
        "Error: Could not reach server";

    console.log(err);

}
      }
           const profilePic =
document.getElementById("profilePic");

const profilePanel =
document.getElementById("profilePanel");

const closeProfile =
document.getElementById("closeProfile");

profilePic.addEventListener("click",()=>{
    profilePanel.classList.add("active");
});

closeProfile.addEventListener("click",()=>{
    profilePanel.classList.remove("active");
});



function createTeachersTable(title,rows){

    let html = `<h3>${title}</h3>`;

    html += `
    <table class="marks-table">
        <tr>
            <th>Subject</th>
            <th>Faculty</th>
            <th>Code</th>
        </tr>
    `;

    rows.forEach(row=>{
        html += `
        <tr>
            <td>${row.subject}</td>
            <td>${row.staff_name}</td>
            <td>${row.subject_code}</td>
        </tr>
        `;
    });

    html += `</table>`;

    return html;
}
function createTodayClasses(title, rows){

    let html = `<h3>${title}</h3>`;

    html += `
    <table class="marks-table">
        <tr>
            <th>Period</th>
            <th>Subject</th>
        </tr>`;

    rows.forEach(row=>{
        html += `
        <tr>
            <td>P${row.period_no}</td>
            <td>${row.subject}</td>
        </tr>`;
    });

    html += `</table>`;

    return html;
}

      function createTable(title, rows, type){
        let html = `<h3>${title}</h3>`;
        html += `<table class="marks-table">`;

          if(type ==="MID-1_Marks"){
            html += `
            <tr>
              <th>Subject</th>
              <th>MID-1</th>
              <th>MID-1_AVG</th>
              </tr>`;
          }
          else if(type==="MID-2_Marks"){
             html += `
            <tr>
              <th>Subject</th>
              <th>MID-2</th>
              <th>MID-2_AVG</th>
              </tr>`;
          }
          else{
            html += `
            <tr>
              <th>Subject</th>
              <th>MID-1</th>
              <th>MID-2</th>
              <th>Final Average</th>
            </tr>`;
          }
          rows.forEach(row=>{
            if(type==="MID-1_Marks"){
              html += `
              <tr>
                <td>${row.subject}</td>
                <td>${row.mid1}</td>
                <td>${row.mid1_avg}</td>
                </tr>`; 
            }
            else if(type==="MID-2_Marks"){
              html +=  `
              <tr>
                <td>${row.subject}</td>
                <td>${row.mid2}</td>
                <td>${row.mid2_avg}</td>
                </tr>`;
            }
            else{
              html +=`
              <tr>
                <td>${row.subject}</td>
                <td>${row.mid1}</td>
                <td>${row.mid2}</td>
                <td>${row.final_avg}</td>
                </tr>`;
              }
            });
            html += `</table>`;
            return html;
      }
     
    
    function appendMessage(text, sender){
      const msgDiv = document.createElement('div');
      msgDiv.classList.add('message',sender);
      msgDiv.innerHTML = text.replace(/\*\*(.*?)\*\*/g,'<b>$1</b>').replace(/\n/g,'<br>');
      chatContainer.appendChild(msgDiv);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      return msgDiv
    }

const notificationBtn = document.getElementById("notificationBtn");
const notificationPanel = document.getElementById("notificationPanel");
const closeNotification = document.getElementById("closeNotification");
const notificationList = document.getElementById("notificationList");
const notificationCount = document.getElementById("notificationCount");
const notificationBadge = document.getElementById("notificationBadge");

// Open notification panel
notificationBtn.addEventListener("click", () => {
    notificationPanel.classList.add("active");
    document.getElementById("profilePanel").classList.remove("active");

    loadNotifications();
});

// Close notification panel
closeNotification.addEventListener("click", () => {
    notificationPanel.classList.remove("active");
});

// Load notifications from Flask
async function loadNotifications() {

    notificationList.innerHTML =
        "<p style='padding:20px;color:#aaa'>Loading notifications...</p>";

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/notifications",
            {
                method: "GET",
                credentials: "include"
            }
        );

        if (!response.ok) {
            throw new Error("Server returned " + response.status);
        }

        const data = await response.json();

        console.log("Notifications:", data);

        if (!data.success) {

            notificationList.innerHTML =
                "<p style='padding:20px;color:#aaa'>" +
                (data.message || "Unable to load notifications.") +
                "</p>";

            notificationCount.innerText = "0";
            notificationBadge.innerText = "0";

            return;
        }

        const notifications = data.notifications || [];

        // Update badge count
        notificationCount.innerText = notifications.length;
        notificationBadge.innerText = notifications.length;

        // No notifications
        if (notifications.length === 0) {

            notificationList.innerHTML =
                "<p style='padding:20px;color:#aaa'>" +
                "No notifications available." +
                "</p>";

            return;
        }

        // Clear old notifications
        notificationList.innerHTML = "";

        // Create notification cards
        notifications.forEach(note => {

            const card = document.createElement("div");
            card.className = "notification-card";

            card.innerHTML = `
                <div class="notification-category">
                    ${note.category || "General"}
                </div>

                <div class="notification-title">
                    ${note.title || "Notification"}
                </div>

                <div class="notification-message">
                    ${note.message || ""}
                </div>

                <div class="notification-date">
                    ${
                        note.created_at
                        ? new Date(note.created_at).toLocaleDateString()
                        : ""
                    }
                </div>
            `;

            notificationList.appendChild(card);

        });

    } catch (error) {

        console.error("Notification error:", error);

        notificationList.innerHTML =
            "<p style='padding:20px;color:#aaa'>" +
            "Unable to load notifications." +
            "</p>";

        notificationCount.innerText = "0";
        notificationBadge.innerText = "0";
    }
}
loadNotifications();