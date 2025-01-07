import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  TextField,
  Typography,
  Paper,
  Divider,
  IconButton,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ReactMarkdown from "react-markdown";

interface Messages {
  user: string[];
  bot: string[];
}

const Chatbot = () => {
  const [messages, setMessages] = useState<Messages>({ user: [], bot: [] });
  const [input, setInput] = useState<string>("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/chatbot");

    websocket.onopen = () => {
      console.log("WebSocket connection established.");
    };

    websocket.onmessage = (event) => {
      setMessages((prevMessages) => {
        const botMessages = [...prevMessages.bot];
        botMessages[botMessages.length - 1] =
          (botMessages[botMessages.length - 1] || "") + event.data;
        return {
          ...prevMessages,
          bot: botMessages,
        };
      });
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    websocket.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() !== "") {
      setMessages((prevMessages) => ({
        user: [...prevMessages.user, input],
        bot: [...prevMessages.bot, ""],
      }));
      ws?.send(input);
      setInput("");
      scrollToBottom();
    } else {
      alert("Please enter a message.");
    }
  };

  const scrollToBottom = () => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100vh", // Full screen height
        backgroundColor: "#242424",
        color: "rgba(255, 255, 255, 0.87)",
      }}
    >
      {/* Sticky Header */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 1,
          backgroundColor: "#1a1a1a",
          color: "white",
          padding: 2,
        }}
      >
        <Typography variant="h6">Chatbot</Typography>
      </Box>

      {/* Scrollable Conversation Section */}
      <Paper
        sx={{
          flex: 1, // Takes available space
          overflowY: "auto", // Only this section scrolls
          padding: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          backgroundColor: "#1a1a1a",
        }}
      >
        {messages.user.map((message, index) => (
          <React.Fragment key={index}>
            <Box
              sx={{
                alignSelf: "flex-end",
                backgroundColor: "#646cff",
                color: "white",
                borderRadius: 2,
                padding: 1,
                maxWidth: "70%",
                wordWrap: "break-word",
              }}
            >
              <ReactMarkdown>{message}</ReactMarkdown>
            </Box>
            <Box
              sx={{
                alignSelf: "flex-start",
                backgroundColor: "#213547",
                color: "white",
                borderRadius: 2,
                padding: 1,
                maxWidth: "70%",
                wordWrap: "break-word",
              }}
            >
              <ReactMarkdown>{messages.bot[index]}</ReactMarkdown>
            </Box>
          </React.Fragment>
        ))}
        <div ref={scrollRef} />
      </Paper>

      {/* Sticky Input Section */}
      <Box
        sx={{
          position: "sticky",
          bottom: 0,
          zIndex: 1,
          backgroundColor: "#1a1a1a",
          padding: 2,
          display: "flex",
          alignItems: "center",
          gap: 1,
        }}
      >
        <TextField
          variant="standard"
          placeholder="Type your message"
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          InputProps={{
            style: { color: "white" },
            disableUnderline: true,
          }}
          sx={{
            backgroundColor: "transparent",
            color: "white",
          }}
        />
        <IconButton onClick={sendMessage}>
          <SendIcon sx={{ color: "#646cff" }} />
        </IconButton>
      </Box>
    </Box>
  );
};

export default Chatbot;
