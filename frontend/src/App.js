import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [cases, setCases] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      const response = await axios.get('http://localhost:8000/cases/');
      setCases(response.data);
    } catch (error) {
      console.error('Error fetching cases:', error);
    }
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);

      files.forEach((file, index) => {
        formData.append(`files`, file);
      });

      const response = await axios.post('http://localhost:8000/cases/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      console.log(response.data);
      setTitle('');
      setDescription('');
      setFiles([]);
      fetchCases(); // Refresh the list
    } catch (error) {
      console.error('Error creating case:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (caseId) => {
    try {
      await axios.delete(`http://localhost:8000/cases/${caseId}`);
      fetchCases(); // Refresh the list
    } catch (error) {
      console.error('Error deleting case:', error);
    }
  };

  return (
    <div className="App">
      <h1>Case Management System</h1>
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Title:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        
        <div>
          <label>Description:</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>
        
        <div>
          <label>Files:</label>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create Case'}
        </button>
      </form>

      <h2>Cases</h2>
      {cases.length === 0 ? (
        <p>No cases available.</p>
      ) : (
        <ul>
          {cases.map((case) => (
            <li key={case.id}>
              <strong>{case.title}</strong> - {case.description}
              <button onClick={() => handleDelete(case.id)}>Delete</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;
