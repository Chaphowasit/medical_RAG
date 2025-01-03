import React, { useState, useEffect } from "react";

// A simple style object to apply to components
const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-end",
    alignItems: "center",
    height: "100vh",
    backgroundColor: "#f0f4f8",
    fontFamily: "'Roboto', sans-serif",
    padding: "20px",
  },
  chatContainer: {
    backgroundColor: "white",
    width: "100%",
    maxWidth: "600px",
    height: "80vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-end",
    padding: "20px",
    borderRadius: "10px",
    boxShadow: "0px 4px 6px rgba(0, 0, 0, 0.1)",
    overflowY: "auto",
  },
  messageContainer: {
    display: "flex",
    flexDirection: "column",
    marginBottom: "10px",
  },
  messageBox: {
    padding: "12px 16px",
    marginBottom: "10px",
    borderRadius: "20px",
    maxWidth: "75%",
    wordBreak: "break-word",
    whiteSpace: "pre-wrap", // Ensures new text is appended without breaking the layout
    display: "inline-block", // Allows continuous streaming in the same box
  },
  userMessageBox: {
    backgroundColor: "#e1e1e1",
    alignSelf: "flex-start",
  },
  botMessageBox: {
    backgroundColor: "#4CAF50",
    color: "white",
    alignSelf: "flex-end",
  },
  inputContainer: {
    display: "flex",
    justifyContent: "space-between",
    width: "100%",
    maxWidth: "600px",
    marginTop: "20px",
  },
  input: {
    width: "80%",
    padding: "10px",
    borderRadius: "20px",
    border: "1px solid #ddd",
    outline: "none",
    fontSize: "16px",
    color: "#333",
    marginRight: "10px",
  },
  button: {
    padding: "10px 20px",
    backgroundColor: "#4CAF50",
    color: "white",
    border: "none",
    borderRadius: "20px",
    cursor: "pointer",
    fontSize: "16px",
  },
};

const ChatbotStream = () => {
  const [messages, setMessages] = useState({ user: "", bot: "" });
  const [input, setInput] = useState("");
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/chatbot");

    websocket.onopen = () => {
      console.log("WebSocket connection established.");
    };

    websocket.onmessage = (event) => {
      // Append incoming message to the bot's message
      setMessages((prevMessages) => ({
        ...prevMessages,
        bot: prevMessages.bot + event.data,
      }));
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    websocket.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    setWs(websocket);

    // Cleanup on unmount
    return () => {
      websocket.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() !== "") {
      setMessages((prevMessages) => ({
        ...prevMessages,
        user: prevMessages.user + input + "\n", // Add a newline after user message for separation
      }));
      ws.send(input); // Send user input to the WebSocket server
      setInput(""); // Clear the input field
    } else {
      alert("Please enter a message.");
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={{ color: "#4CAF50", marginBottom: "20px" }}>Chatbot</h1>
      <div style={styles.chatContainer}>
        {/* Display user and bot messages in the same text box */}
        <div style={styles.messageBox}>
          <div
            style={{
              ...styles.userMessageBox,
              whiteSpace: "pre-wrap", // This ensures text remains in a single block
            }}
          >
            {messages.user}
          </div>
          <div
            style={{
              ...styles.botMessageBox,
              whiteSpace: "pre-wrap", // This ensures bot's text streams continuously in the same box
            }}
          >
            {messages.bot}
          </div>
        </div>
      </div>

      <div style={styles.inputContainer}>
        <input
          id="query"
          type="text"
          placeholder="Type your message here"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={styles.input}
        />
        <button onClick={sendMessage} style={styles.button}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatbotStream;
