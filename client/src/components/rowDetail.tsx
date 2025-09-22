"use client"

import React from 'react'

interface RowDetailProps {
  data: any
}

export function RowDetail({ data }: RowDetailProps) {
  return (
    <div className="bg-gray-50 dark:bg-gray-800 p-6 border-t border-gray-200 dark:border-gray-600">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">Summary</h4>
            <div className="text-sm bg-white dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600 min-h-[80px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-gray-900 dark:text-gray-100">
                {data.summary || <span className="text-gray-500 dark:text-gray-400 italic">No summary available</span>}
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">Customer Intent</h4>
            <div className="text-sm bg-white dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600 min-h-[80px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-gray-900 dark:text-gray-100">
                {data.customer_intent || <span className="text-gray-500 dark:text-gray-400 italic">No intent identified</span>}
              </p>
            </div>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">Quality Score</h4>
            <div className="text-sm bg-white dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600">
              {data.quality_score !== null && data.quality_score !== undefined ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-lg text-gray-900 dark:text-gray-100">{data.quality_score.toFixed(2)}</span>
                    <span className="text-gray-500 dark:text-gray-400 text-sm">/10</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(data.quality_score / 10) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Quality assessment based on call analysis
                  </p>
                </div>
              ) : (
                <span className="text-gray-500 dark:text-gray-400 italic">No quality score available</span>
              )}
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">Transcript</h4>
            <div className="text-sm bg-white dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600 min-h-[120px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-gray-900 dark:text-gray-100">
                {data.transcript || <span className="text-gray-500 dark:text-gray-400 italic">No transcript available</span>}
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 text-base">Audio Recording</h4>
            <div className="text-sm bg-white dark:bg-gray-700 p-4 rounded border border-gray-200 dark:border-gray-600">
              {data.recording_url ? (
                <div className="space-y-3">
                  <audio 
                    controls 
                    className="w-full"
                    preload="metadata"
                  >
                    <source src={data.recording_url} type="audio/mpeg" />
                    <source src={data.recording_url} type="audio/wav" />
                    <source src={data.recording_url} type="audio/mp3" />
                    Your browser does not support the audio element.
                  </audio>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <a 
                      href={data.recording_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline"
                    >
                      Download audio file
                    </a>
                  </div>
                </div>
              ) : (
                <span className="text-gray-500 dark:text-gray-400 italic">No audio recording available</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
