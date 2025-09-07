"use client"

import React from 'react'

interface RowDetailProps {
  data: any
}

export function RowDetail({ data }: RowDetailProps) {
  return (
    <div className="bg-gray-50 p-4 border-t border-gray-200">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700">Summary</h4>
            <div className="text-sm bg-white p-3 rounded border">
              {data.summary || <span className="text-gray-500 italic">No summary available</span>}
            </div>
          </div>
          
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700">Customer Intent</h4>
            <div className="text-sm bg-white p-3 rounded border">
              {data.customer_intent || <span className="text-gray-500 italic">No intent identified</span>}
            </div>
          </div>
        </div>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700">Quality Score</h4>
            <div className="text-sm bg-white p-3 rounded border">
              {data.quality_score !== null && data.quality_score !== undefined ? (
                <div className="flex items-center gap-2">
                  <span className="font-medium">{data.quality_score.toFixed(2)}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        data.quality_score >= 0.8 ? 'bg-green-500' :
                        data.quality_score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${data.quality_score * 100}%` }}
                    ></div>
                  </div>
                </div>
              ) : (
                <span className="text-gray-500 italic">No quality score available</span>
              )}
            </div>
          </div>
          
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700">Transcript</h4>
            <div className="text-sm bg-white p-3 rounded border max-h-32 overflow-y-auto">
              {data.transcript || <span className="text-gray-500 italic">No transcript available</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
