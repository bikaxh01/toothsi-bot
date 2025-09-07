"use client"

import React from 'react'

interface RowDetailProps {
  data: any
}

export function RowDetail({ data }: RowDetailProps) {
  return (
    <div className="bg-gray-50 p-6 border-t border-gray-200">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 text-base">Summary</h4>
            <div className="text-sm bg-white p-4 rounded border min-h-[80px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere">
                {data.summary || <span className="text-gray-500 italic">No summary available</span>}
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 text-base">Customer Intent</h4>
            <div className="text-sm bg-white p-4 rounded border min-h-[80px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere">
                {data.customer_intent || <span className="text-gray-500 italic">No intent identified</span>}
              </p>
            </div>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 text-base">Quality Score</h4>
            <div className="text-sm bg-white p-4 rounded border">
              {data.quality_score !== null && data.quality_score !== undefined ? (
                <span className="font-medium text-lg">{data.quality_score.toFixed(2)}</span>
              ) : (
                <span className="text-gray-500 italic">No quality score available</span>
              )}
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-700 text-base">Transcript</h4>
            <div className="text-sm bg-white p-4 rounded border min-h-[120px] max-h-[200px] w-full overflow-y-auto overflow-x-hidden">
              <p className="whitespace-pre-wrap break-words overflow-wrap-anywhere">
                {data.transcript || <span className="text-gray-500 italic">No transcript available</span>}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
