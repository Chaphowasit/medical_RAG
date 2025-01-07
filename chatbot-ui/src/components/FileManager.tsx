import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  Container,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Typography,
} from "@mui/material";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import axios from "axios";

const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#242424",
      paper: "#242424",
    },
    text: {
      primary: "rgba(255, 255, 255, 0.87)",
    },
  },
});

const FileManager: React.FC = () => {
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchFiles = async () => {
    try {
      const response = await axios.get("http://localhost:8000/files/list");
      setFiles(response.data.filenames || []);
    } catch (error) {
      console.error("Error fetching files:", error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;

    const file = event.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post("http://localhost:8000/files/create", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      fetchFiles(); // Refresh the file list
    } catch (error) {
      console.error("Error uploading file:", error);
    }
  };

  const handleFileDelete = async (filename: string) => {
    try {
      await axios.delete(`http://localhost:8000/files/delete`, {
        params: { filename },
      });
      fetchFiles(); // Refresh the file list
    } catch (error) {
      console.error("Error deleting file:", error);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="sm" sx={{ padding: "2rem" }}>
        <Typography variant="h4" gutterBottom>
          File Manager
        </Typography>
        <Box>
          <Button variant="contained" component="label" sx={{ marginBottom: "1rem" }}>
            Upload File
            <input type="file" hidden onChange={handleFileUpload} />
          </Button>
        </Box>
        <List>
          {files.map((file, index) => (
            <ListItem key={index} divider>
              <ListItemText primary={file} />
              <ListItemSecondaryAction>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => handleFileDelete(file)}
                >
                  Delete
                </Button>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Container>
    </ThemeProvider>
  );
};

export default FileManager;
