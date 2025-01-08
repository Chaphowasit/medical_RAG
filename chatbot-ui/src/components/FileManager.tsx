import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Container,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Snackbar,
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
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetchFiles = async () => {
    console.log("Fetching file list...");
    setLoading(true);
    try {
      const response = await axios.get("http://localhost:8000/files/list");
      console.log("Files fetched successfully:", response.data.filenames);
      setFiles(response.data.filenames || []);
    } catch (error) {
      console.error("Error fetching files:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;

    const file = event.target.files[0];
    console.log("Uploading file:", file.name);

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setMessage("Uploading...");
    try {
      const response = await axios.post("http://localhost:8000/files/create", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      console.log("File uploaded successfully:", response.data);
      setMessage("File uploaded successfully!");
      fetchFiles(); // Refresh the file list
    } catch (error) {
      console.error("Error uploading file:", error);
      setMessage("Error uploading file!");
    } finally {
      setLoading(false);
    }
  };

  const handleFileDelete = async (filename: string) => {
    console.log("Deleting file:", filename);
    setLoading(true);
    setMessage("Deleting...");
    try {
      const response = await axios.delete(`http://localhost:8000/files/delete`, {
        params: { filename },
      });
      console.log("File deleted successfully:", response.data);
      setMessage("File deleted successfully!");
      fetchFiles(); // Refresh the file list
    } catch (error) {
      console.error("Error deleting file:", error);
      setMessage("Error deleting file!");
    } finally {
      setLoading(false);
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
          <Button
            variant="contained"
            component="label"
            sx={{ marginBottom: "1rem" }}
            disabled={loading} // Disable button while loading
          >
            Upload File
            <input type="file" hidden onChange={handleFileUpload} />
          </Button>
        </Box>
        {loading && (
          <Box display="flex" justifyContent="center" sx={{ marginBottom: "1rem" }}>
            <CircularProgress />
          </Box>
        )}
        <List>
          {files.map((file, index) => (
            <ListItem key={index} divider>
              <ListItemText primary={file} />
              <ListItemSecondaryAction>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => handleFileDelete(file)}
                  disabled={loading} // Disable button while loading
                >
                  Delete
                </Button>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
        <Snackbar
          open={!!message}
          autoHideDuration={3000}
          onClose={() => setMessage(null)}
          message={message}
        />
      </Container>
    </ThemeProvider>
  );
};

export default FileManager;
