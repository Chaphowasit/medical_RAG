import { useState } from "react";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemText, Typography } from "@mui/material";
import Chatbot from "./components/Chatbot";
import FileManager from "./components/FileManager";

function App() {
  const [selectedTab, setSelectedTab] = useState<string>("Chatbot");

  const renderContent = () => {
    switch (selectedTab) {
      case "Chatbot":
        return <Chatbot />;
      case "FileManager":
        return <FileManager />;
      default:
        return null;
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        width: "100vw",
        height: "100vh",
      }}
    >
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        anchor="left"
        sx={{
          width: 240,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: 240,
            boxSizing: "border-box",
            backgroundColor: "#242424",
            color: "rgba(255, 255, 255, 0.87)",
          },
        }}
      >
        <Typography
          variant="h5"
          sx={{
            textAlign: "center",
            padding: "1rem 0",
            borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
          }}
        >
          Navigator
        </Typography>
        <List>
          
          <ListItem disablePadding>
            <ListItemButton
              selected={selectedTab === "Chatbot"}
              onClick={() => setSelectedTab("Chatbot")}
              sx={{
                backgroundColor: selectedTab === "Chatbot" ? "rgba(255, 255, 255, 0.2)" : "inherit",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 0.1)",
                },
              }}
            >
              <ListItemText primary="Chatbot" />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton
              selected={selectedTab === "FileManager"}
              onClick={() => setSelectedTab("FileManager")}
              sx={{
                backgroundColor: selectedTab === "FileManager" ? "rgba(255, 255, 255, 0.2)" : "inherit",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 0.1)",
                },
              }}
            >
              <ListItemText primary="File Manager" />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>

      {/* Main Content */}
      <Box
        sx={{
          flexGrow: 1,
        }}
      >
        {renderContent()}
      </Box>
    </Box>
  );
}

export default App;
