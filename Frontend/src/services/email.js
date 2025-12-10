import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const emailAPI = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const sendContactEmail = async (formData) => {
  try {
    const response = await emailAPI.post("/api/contact", {
      name: formData.name,
      email: formData.email,
      subject: formData.subject,
      message: formData.message,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export default emailAPI;
