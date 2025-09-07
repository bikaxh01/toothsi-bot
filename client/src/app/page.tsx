"use client";
import Image from "next/image";
import MyDropzone from "../components/dropBox";
import { useState, useCallback, useEffect, useRef } from "react";
import { DataTable } from "@/components/dataTable";
import axios from "axios";
const columns = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "phone",
    header: "Phone",
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }: { row: any }) => (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
        row.getValue("status") === "initiated" 
          ? "bg-blue-100 text-blue-800" 
          : row.getValue("status") === "completed"
          ? "bg-green-100 text-green-800"
          : "bg-gray-100 text-gray-800"
      }`}>
        {row.getValue("status")}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Created At",
    cell: ({ row }: { row: any }) => {
      const date = new Date(row.getValue("created_at"));
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    },
  },
];

export default function Home() {
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [data, setData] = useState([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to fetch call details from the batch
  const fetchCallDetails = useCallback(async (batchId: string) => {
    try {
      const serverBaseUrl =
        process.env.NEXT_PUBLIC_SERVER_BASE_URL || "http://localhost:3001";
      const response = await axios.get(`${serverBaseUrl}/calls/batch/${batchId}`);
      
      // Transform the data to match table structure with new fields
      const transformedData = response.data.calls.map((call: any) => ({
        id: call.id,
        batch_id: call.batch_id,
        name: call.user?.name || 'N/A',
        email: call.user?.email || 'N/A',
        phone: call.user?.phone || 'N/A',
        status: call.status,
        created_at: call.created_at,
        updated_at: call.updated_at,
        summary: call.call_result?.summary || null,
        transcript: call.call_result?.transcript || null,
        quality_score: call.call_result?.quality_score || null,
        customer_intent: call.call_result?.customer_intent || null
      }));
      
      setData(transformedData);
      console.log("Updated call details:", transformedData);
    } catch (error) {
      console.error("Error fetching call details:", error);
    }
  }, []);

  // Start polling function
  const startPolling = useCallback((batchId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    
    setIsPolling(true);
    // Fetch immediately
    fetchCallDetails(batchId);
    
    // Then poll every 30 seconds
    pollingIntervalRef.current = setInterval(() => {
      fetchCallDetails(batchId);
    }, 30000);
  }, [fetchCallDetails]);

  // Stop polling function
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Cleanup polling on component unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploadStatus("uploading");
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const serverBaseUrl =
        process.env.NEXT_PUBLIC_SERVER_BASE_URL || "http://localhost:3001";
      const response = await axios.post(`${serverBaseUrl}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setUploadStatus("success");
      setUploadMessage("File uploaded successfully!");
      console.log("Upload response:", response.data);
      
      // Extract batch_id from the response
      const batchId = response.data.batch_id || response.data.calls?.[0]?.batch_id;
      if (batchId) {
        setBatchId(batchId);
        // Start polling for call details
        startPolling(batchId);
      } else {
        console.error("No batch_id found in upload response");
      }
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage("Upload failed. Please try again.");
      console.error("Upload error:", error);
      // Stop any existing polling
      stopPolling();
    }
  }, [startPolling, stopPolling]);

  return (
    <>
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        {uploadStatus !== "success" && (
          <div className="mb-8">
            <MyDropzone
              onDrop={onDrop}
              uploadStatus={uploadStatus}
              uploadMessage={uploadMessage}
            />
          </div>
        )}
        {data.length > 0 && (
          <div className="w-full max-w-6xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Uploaded Data</h2>
              {isPolling && (
                <div className="flex items-center gap-2 text-sm text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span>Polling for updates...</span>
                </div>
              )}
            </div>
            <DataTable columns={columns} data={data} />
          </div>
        )}
      </div>
    </>
  );
}
