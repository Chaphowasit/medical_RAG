import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  TextField,
  Typography,
  Paper,
  Divider,
  IconButton,
  CircularProgress,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ReactMarkdown from "react-markdown";

interface Messages {
  user: string[];
  bot: { message: string; source: string }[];
}

const Chatbot = () => {
  const [messages, setMessages] = useState<Messages>({ user: [], bot: [] });
  const [input, setInput] = useState<string>("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/chatbot");

    websocket.onopen = () => {
      console.log("WebSocket connection established.");
    };

    websocket.onmessage = (event) => {
      try {
        // Parse the response JSON
        const data = JSON.parse(event.data);

        // Extract relevant response fields
        const botMessage = data.response || "";
        const botSource = data.source || "";

        setMessages((prevMessages) => {
          const botMessages = [...prevMessages.bot];
          botMessages[botMessages.length - 1] = {
            message: (botMessages[botMessages.length - 1]?.message || "") + botMessage,
            source: botSource,
          };
          return {
            ...prevMessages,
            bot: botMessages,
          };
        });

        setLoading(false); // Stop animation when response is received
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
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
        bot: [...prevMessages.bot, { message: "", source: "" }],
      }));
      ws?.send(input);
      setInput("");
      setLoading(true); // Start animation
      scrollToBottom();
    }
  };

  const scrollToBottom = () => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
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
          flex: 1,
          overflowY: "auto",
          padding: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          backgroundColor: "#1a1a1a",
        }}
      >
        {messages.user.map((message, index) => (
          <React.Fragment key={index}>
            {/* User message */}
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

            {/* Bot message */}
            <Box
              sx={{
                alignSelf: "flex-start",
                backgroundColor: "#213547",
                color: "white",
                borderRadius: 2,
                padding: 1,
                maxWidth: "70%",
                wordWrap: "break-word",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {index === messages.user.length - 1 && loading ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <ReactMarkdown>{messages.bot[index]?.message}</ReactMarkdown>
              )}
              <Divider sx={{ backgroundColor: "rgba(255, 255, 255, 0.2)", marginY: 0.5 }} />
              <Typography
                variant="caption"
                sx={{ alignSelf: "flex-end", color: "rgba(255, 255, 255, 0.6)" }}
              >
                Source: {messages.bot[index]?.source || "Unknown"}
              </Typography>
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
          onKeyDown={handleKeyDown}
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
