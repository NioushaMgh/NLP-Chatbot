const chatHistoryElement = document.getElementById("chatHistory");
        const chatForm = document.getElementById("chatForm");
        const chatInput = document.getElementById("chatInput");
        const clearChatBtn = document.getElementById("clearChatBtn");

        // Local storage for chat history, active jobs, completed jobs, and pending jobs
        const chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];
        const activeJobs = JSON.parse(localStorage.getItem("activeJobs")) || {};
        const completedJobs = JSON.parse(localStorage.getItem("completedJobs")) || {}; 
        const pendingJobs = JSON.parse(localStorage.getItem("pendingJobs")) || {}; 
        const jobStatus = {}; 

        // Render chat history on page load
        function loadChatHistory() {
            chatHistory.forEach(({ message, type }) => appendMessage(message, type));
        }

        function appendMessage(message, type) {
            const lastMessage = chatHistoryElement.lastChild;
            if (lastMessage && lastMessage.textContent === message) {
                return;
            }
        
            const messageElement = document.createElement("div");
            messageElement.className = `chat-message ${type}`;
        
            // انتقال "منبع مرتبط" به خط جدید
            const formattedMessage = message.replace(
                /(منبع :)/g,
                '<br><div>$1</div>'
            ).replace(
                /(https?:\/\/[^\s]+)/g,
                '<div><a href="$1" target="_blank" rel="noopener noreferrer">$1</a></div>'
            );
            
        
            messageElement.innerHTML = formattedMessage; // درج محتوای HTML با فرمت مناسب
            chatHistoryElement.appendChild(messageElement);
        
            chatHistoryElement.scrollTop = chatHistoryElement.scrollHeight;
        }
        

        // Save chat history, active jobs, completed jobs, and pending jobs to localStorage
        function saveToLocalStorage() {
            localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
            localStorage.setItem("activeJobs", JSON.stringify(activeJobs));
            localStorage.setItem("completedJobs", JSON.stringify(completedJobs));
            localStorage.setItem("pendingJobs", JSON.stringify(pendingJobs)); 
        }

        // Submit chat question
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const question = chatInput.value.trim();
            if (!question) return;

            // Add user question to chat
            appendMessage(question, "user");
            chatHistory.push({ message: question, type: "user" });
            saveToLocalStorage();

            chatInput.value = "";

            // Check if this job is already in the pending jobs list
            if (Object.values(pendingJobs).includes(question)) {
                console.log("Job already pending or processed, skipping.");
                return;
            }

            // Send question to backend
            const jobID = await createJob(question);
            if (jobID) {
                activeJobs[jobID] = { question };
                pendingJobs[jobID] = question; // Mark the job as pending
                saveToLocalStorage();
                pollJobStatus(jobID);
            }
        });

        // Create a job on the backend
        async function createJob(question) {
            try {
                const response = await fetch("http://localhost:8080/query", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question }),
                });

                if (!response.ok) throw new Error("عدم توانایی در ایجاد درخواست");
                const { job_id } = await response.json();
                return job_id;
            } catch (error) {
                appendMessage("خطا: قادر به ایجاد درخواست نمی‌باشیم.", "system");
                chatHistory.push({ message: "خطا: قادر به ایجاد درخواست نمی‌باشیم.", type: "system" });
                saveToLocalStorage();
                return null;
            }
        }

        // Poll job status every 20 minutes
        function pollJobStatus(jobID) {
            // Avoid creating multiple EventSource instances for the same job
            if (jobStatus[jobID]) {
                console.log(`Job ${jobID} is already being tracked.`);
                return;
            }

            // Check if the job is already completed or still pending
            if (completedJobs[jobID]) {
                console.log(`Job ${jobID} has already been completed. Skipping polling.`);
                return;
            }

            const eventSource = new EventSource(`http://localhost:8080/status?job_id=${jobID}`);
            jobStatus[jobID] = eventSource; // Mark the job as being tracked

            eventSource.onmessage = (event) => {
                console.log("دریافت بروزرسانی:", event.data);
                appendMessage(`بروزرسانی: ${event.data}`, "system");
            };

            eventSource.addEventListener("processing", (event) => {
                console.log("در حال پردازش:", event.data);
            });

            eventSource.addEventListener("completed", (event) => {
                try {
                    const response = JSON.parse(event.data);
                    console.log("Response Data: ", response);

                    if (response.status === "completed" && response.result) {
                        const fullText = cleanText(response.result);

                        // Extract the relevant sections from the fullText
                        const contextStartIndex = fullText.indexOf("قوانین مرتبط:");
                        const questionStartIndex = fullText.indexOf("لطفاً یک پاسخ دقیق");
                        const responseStartIndex = fullText.indexOf("لطفاً یک پاسخ دقیق، کامل و مبتنی بر قوانین مرتبط ارائه دهید:") + 
                                                "لطفاً یک پاسخ دقیق، کامل و مبتنی بر قوانین مرتبط ارائه دهید: ".length;

                        const contextText = fullText.substring(contextStartIndex, questionStartIndex)?.trim(); // قوانین مرتبط
                        const resultText = fullText.substring(responseStartIndex)?.trim(); // پاسخ دقیق

                        // Add the regulations message to the UI
                        if (contextText) {
                            appendMessage(`قوانین مرتبط :\n${contextText}`, "bot");
                            chatHistory.push({ message: `\n${contextText}`, type: "bot" });
                        }

                        // Add the model's answer message to the UI
                        if (resultText) {
                            appendMessage(`پاسخ مدل :\n${resultText}`, "bot");
                            chatHistory.push({ message: `پاسخ مدل :\n${resultText}`, type: "bot" });
                        }
                    } else {
                        appendMessage("پاسخ بات: درخواست تکمیل شد، ولی هیچ نتیجه‌ای ارائه نشد.", "bot");
                        chatHistory.push({ message: "پاسخ بات: درخواست تکمیل شد، ولی هیچ نتیجه‌ای ارائه نشد.", type: "bot" });
                    }

                    // Mark job as completed
                    completedJobs[jobID] = true;
                    delete pendingJobs[jobID]; // Remove the job from pending jobs
                    saveToLocalStorage();

                } catch (error) {
                    console.error("خطا در تجزیه داده‌های تکمیل شده:", error);
                    appendMessage("پاسخ بات: نتواستیم پاسخی پیدا کنیم.", "bot");
                    chatHistory.push({ message: "پاسخ بات: نتواستیم پاسخی پیدا کنیم.", type: "bot" });
                }
                saveToLocalStorage();
                eventSource.close(); // Stop listening after completion
                delete jobStatus[jobID]; // Remove from tracked jobs after completion
            });

            eventSource.addEventListener("error", (event) => {
                console.error("خطا:", event.data);
                appendMessage("یک خطا رخ داد.", "system");
                eventSource.close();
                delete jobStatus[jobID]; // Remove from tracked jobs on error
            });

            eventSource.onerror = () => {
                console.error("خطا در ارتباط SSE. قطع ارتباط.");
                appendMessage("اتصال قطع شد. در حال تلاش مجدد...", "system");
            };
        }

        // Function to clean unwanted characters
        function cleanText(text) {
            if (typeof text !== 'string') {
                return ''; // Return an empty string if the text is not valid
            }
            return text.replace(/\u200c/g, '').replace(/\s+/g, ' ').trim();
        }

        // Clear chat history
        clearChatBtn.addEventListener("click", () => {
            localStorage.removeItem("chatHistory");
            localStorage.removeItem("activeJobs");
            localStorage.removeItem("completedJobs");
            localStorage.removeItem("pendingJobs"); // Clear pending jobs
            window.location.reload();
        });

        loadChatHistory();
        Object.keys(activeJobs).forEach((jobID) => pollJobStatus(jobID));
