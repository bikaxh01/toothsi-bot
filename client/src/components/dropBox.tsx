"use client"

import React, {useCallback, useState} from 'react'
import {useDropzone} from 'react-dropzone'
import axios from 'axios'

function MyDropzone({onDrop, uploadStatus, uploadMessage}: {onDrop: (acceptedFiles: File[]) => void, uploadStatus: "idle" | "uploading" | "success" | "error", uploadMessage: string}) {
 
  const {getRootProps, getInputProps, isDragActive, fileRejections} = useDropzone({
    onDrop,
    accept: {
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    maxFiles: 1,
    multiple: false,
    disabled: uploadStatus === 'uploading'
  })

  return (
    <div className="w-full max-w-[340px] mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-2xl transition-colors duration-200 min-h-[320px] w-full flex flex-col items-center justify-center px-6 py-12 ${
          uploadStatus === 'uploading' 
            ? 'cursor-not-allowed bg-gray-50 dark:bg-gray-800' 
            : isDragActive 
            ? 'bg-gray-100 dark:bg-gray-700 cursor-pointer' 
            : 'bg-white dark:bg-gray-800 cursor-pointer'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-6">
          <div className={`rounded-full w-16 h-16 flex items-center justify-center mb-2 ${
            uploadStatus === 'uploading' ? 'bg-blue-50 dark:bg-blue-900' : 'bg-gray-50 dark:bg-gray-700'
          }`}>
            {uploadStatus === 'uploading' ? (
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            ) : uploadStatus === 'success' ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#10B981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : uploadStatus === 'error' ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 16V8M12 8L8 12M12 8L16 12" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <rect x="3" y="3" width="18" height="18" rx="4" stroke="#D1D5DB" strokeWidth="2"/>
              </svg>
            )}
          </div>
          <span className={`text-base font-medium text-center leading-relaxed ${
            uploadStatus === 'uploading' ? 'text-blue-600 dark:text-blue-400' : 
            uploadStatus === 'success' ? 'text-green-600 dark:text-green-400' :
            uploadStatus === 'error' ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'
          }`}>
            {uploadStatus === 'uploading' ? 'Uploading...' :
             uploadStatus === 'success' ? 'File uploaded successfully!' :
             uploadStatus === 'error' ? 'Upload failed' :
             'Drop Excel file or click\nhere to upload'}
          </span>
          <span className="text-gray-400 dark:text-gray-500 text-sm text-center">
            Only .xls and .xlsx files allowed
          </span>
        </div>
      </div>
      
      {/* Upload status message */}
      {uploadMessage && (
        <div className={`mt-4 p-3 rounded-lg ${
          uploadStatus === 'success' 
            ? 'bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700' 
            : uploadStatus === 'error' 
            ? 'bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700' 
            : 'bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700'
        }`}>
          <p className={`text-sm ${
            uploadStatus === 'success' 
              ? 'text-green-600 dark:text-green-400' 
              : uploadStatus === 'error' 
              ? 'text-red-600 dark:text-red-400' 
              : 'text-blue-600 dark:text-blue-400'
          }`}>
            {uploadMessage}
          </p>
        </div>
      )}

      {/* File rejection errors */}
      {fileRejections.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-lg">
          <p className="text-red-600 dark:text-red-400 text-sm">
            {fileRejections[0].errors[0].code === 'file-invalid-type' 
              ? 'Please upload only .xls or .xlsx files'
              : fileRejections[0].errors[0].code === 'too-many-files'
              ? 'Please upload only one file at a time'
              : 'File upload failed. Please try again.'}
          </p>
        </div>
      )}
    </div>
  )
}

export default MyDropzone