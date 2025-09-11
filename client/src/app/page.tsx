"use client";
import MyDropzone from "../components/dropBox";
import { useState, useCallback, useEffect, useRef } from "react";
import { DataTable } from "@/components/dataTable";
import { AuthDialog } from "@/components/authDialog";
import { useAuth } from "@/hooks/useAuth";
import axios from "axios";


// Columns for batches table
const batchesColumns = [
  {
    accessorKey: "file_name",
    header: "File Name",
  },
  {
    accessorKey: "created_at",
    header: "Created At",
    cell: ({ row }: { row: any }) => {
      const date = new Date(row.getValue("created_at"));
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    },
  },
  {
    accessorKey: "id",
    header: "Batch ID",
    cell: ({ row }: { row: any }) => (
      <span className="font-mono text-sm text-gray-600">
        {row.getValue("id").substring(0, 8)}...
      </span>
    ),
  },
];

export default function Home() {
  const { isAuthenticated, isLoading, authenticate, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<"upload" | "files" | "details">("upload");
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [callDetailsData, setCallDetailsData] = useState([]);
  const [batchesData, setBatchesData] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [redialingCalls, setRedialingCalls] = useState<Set<string>>(new Set());

  // Function to fetch batches from /batches endpoint
  const fetchBatches = useCallback(async () => {
    try {
      const serverBaseUrl =
        process.env.NEXT_PUBLIC_SERVER_BASE_URL || "http://localhost:3001";
      const response = await axios.get(`${serverBaseUrl}/batches`);
      setBatchesData(response.data.batches || []);
      console.log("Fetched batches:", response.data.batches);
    } catch (error) {
      console.error("Error fetching batches:", error);
    }
  }, []);

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
        customer_intent: call.call_result?.customer_intent || null,
        recording_url: call.call_result?.recording_url || null
      }));
      
      setCallDetailsData(transformedData);
      console.log("Updated call details:", transformedData);
    } catch (error) {
      console.error("Error fetching call details:", error);
    }
  }, []);

  // Function to redial a call
  const redialCall = useCallback(async (callId: string) => {
    console.log("Redialing call with ID:", callId);
    
    if (!callId) {
      console.error("No call ID provided for redial");
      alert("Error: No call ID found. Please refresh and try again.");
      return;
    }
    
    try {
      setRedialingCalls(prev => new Set(prev).add(callId));
      
      const serverBaseUrl =
        process.env.NEXT_PUBLIC_SERVER_BASE_URL || "http://localhost:3001";
      const response = await axios.post(`${serverBaseUrl}/calls/${callId}/redial`);
      
      console.log("Redial response:", response.data);
      
      // Show success message (you could add a toast notification here)
      alert(`Call redialed successfully! New call ID: ${response.data.vapi_call_id}`);
      
      // Refresh the call details to show updated status
      if (selectedBatchId) {
        fetchCallDetails(selectedBatchId);
      }
    } catch (error) {
      console.error("Error redialing call:", error);
      alert("Failed to redial call. Please try again.");
    } finally {
      setRedialingCalls(prev => {
        const newSet = new Set(prev);
        newSet.delete(callId);
        return newSet;
      });
    }
  }, [selectedBatchId, fetchCallDetails]);

  // Columns for call details table
  const callDetailsColumns = [
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
      accessorKey: "quality_score",
      header: "Quality Score",
      cell: ({ row }: { row: any }) => {
        const score = row.getValue("quality_score");
        return score ? `${score}/10` : "N/A";
      },
    },
    {
      accessorKey: "created_at",
      header: "Created At",
      cell: ({ row }: { row: any }) => {
        const date = new Date(row.getValue("created_at"));
        return date.toLocaleDateString() + " " + date.toLocaleTimeString();
      },
    },
    {
      id: "redial",
      header: "Actions",
      cell: ({ row }: { row: any }) => {
        const callId = row.original.id;
        const isRedialing = redialingCalls.has(callId);
        
        // Debug logging
        console.log("Row data:", row.original);
        console.log("Call ID:", callId);
        
        return (
          <button
            onClick={(e) => {
              e.stopPropagation(); // Prevent row expansion
              redialCall(callId);
            }}
            disabled={isRedialing || !callId}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              isRedialing || !callId
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-red-600 text-white hover:bg-red-700"
            }`}
          >
            {isRedialing ? (
              <div className="flex items-center gap-1">
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-400"></div>
                <span>Redialing...</span>
              </div>
            ) : (
              "Redial"
            )}
          </button>
        );
      },
    },
  ];

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

  // Fetch batches when component mounts
  useEffect(() => {
    fetchBatches();
  }, [fetchBatches]);

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
        setSelectedBatchId(batchId);
        // Refresh batches list
        fetchBatches();
        // Switch to details tab and start polling
        setActiveTab("details");
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
  }, [startPolling, stopPolling, fetchBatches]);

  // Handle batch selection from files tab
  const handleBatchSelect = useCallback((batchId: string) => {
    setSelectedBatchId(batchId);
    setActiveTab("details");
    startPolling(batchId);
  }, [startPolling]);

  // Custom batches table with clickable rows
  const BatchesTable = ({ data }: { data: any[] }) => {
    return (
      <div className="overflow-hidden rounded-md border">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {batchesColumns.map((column) => (
                <th key={column.accessorKey} className="px-4 py-3 text-left text-sm font-medium text-gray-900">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length > 0 ? (
              data.map((batch) => (
                <tr
                  key={batch.id}
                  className="cursor-pointer hover:bg-gray-50 transition-colors border-b"
                  onClick={() => handleBatchSelect(batch.id)}
                >
                  {batchesColumns.map((column) => (
                    <td key={column.accessorKey} className="px-4 py-3 text-sm text-gray-900">
                      {column.cell ? column.cell({ row: { getValue: (key: string) => batch[key] } }) : batch[column.accessorKey]}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={batchesColumns.length} className="h-24 text-center text-gray-500">
                  No batches found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show authentication dialog if not authenticated
  if (!isAuthenticated) {
    return <AuthDialog isOpen={true} onAuthenticated={authenticate} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Toothsi Dashboard</h1>
              <p className="text-gray-600 mt-2">Upload files, view batches, and monitor call details</p>
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: "upload", label: "Upload" },
                { id: "files", label: "Files" },
                { id: "details", label: "Details" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-sm border">
          {activeTab === "upload" && (
            <div className="p-8">
              <h2 className="text-xl font-semibold mb-6">Upload File</h2>
              <div className="flex justify-center">
                <MyDropzone
                  onDrop={onDrop}
                  uploadStatus={uploadStatus}
                  uploadMessage={uploadMessage}
                />
              </div>
            </div>
          )}

          {activeTab === "files" && (
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">All Files</h2>
                <button
                  onClick={fetchBatches}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Refresh
                </button>
              </div>
              <BatchesTable data={batchesData} />
            </div>
          )}

          {activeTab === "details" && (
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">
                  Call Details {selectedBatchId && `(Batch: ${selectedBatchId.substring(0, 8)}...)`}
                </h2>
                {isPolling && (
                  <div className="flex items-center gap-2 text-sm text-blue-600">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span>Polling for updates...</span>
                  </div>
                )}
              </div>
              {selectedBatchId ? (
                <DataTable columns={callDetailsColumns} data={callDetailsData} />
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <p>Select a batch from the Files tab to view call details</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
