'use client';

import { useState } from 'react';

export default function Dashboard() {
  const [orders, setOrders] = useState([
    {
      id: 'ORD001',
      topic: 'The Fall of Constantinople',
      status: 'Delivered',
      date: '2024-06-01',
    },
    {
      id: 'ORD002',
      topic: 'Quantum Entanglement Explained',
      status: 'Production',
      date: '2024-06-15',
    },
  ]);

  const [showForm, setShowForm] = useState(false);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Dashboard
          </h2>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          <button
            onClick={() => setShowForm(!showForm)}
            type="button"
            className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            {showForm ? 'Cancel' : 'Submit New Brief'}
          </button>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Subscription Info */}
        <div className="overflow-hidden rounded-lg bg-white shadow ring-1 ring-gray-900/5">
          <div className="p-6">
            <h3 className="text-base font-semibold leading-6 text-gray-900">Subscription Status</h3>
            <div className="mt-4">
              <p className="text-sm text-gray-500">Tier: <span className="font-semibold text-indigo-600">Intermediate</span></p>
              <p className="text-sm text-gray-500">Videos remaining this month: <span className="font-semibold text-gray-900">1 / 2</span></p>
              <p className="text-sm text-gray-500 mt-2">Next billing date: July 25, 2024</p>
            </div>
            <div className="mt-6">
              <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
                Manage Subscription &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Order History */}
        <div className="lg:col-span-2 overflow-hidden rounded-lg bg-white shadow ring-1 ring-gray-900/5">
          <div className="p-6">
            <h3 className="text-base font-semibold leading-6 text-gray-900">Your Videos</h3>
            <div className="mt-6 flow-root">
              <ul role="list" className="-my-5 divide-y divide-gray-200">
                {orders.map((order) => (
                  <li key={order.id} className="py-5">
                    <div className="relative focus-within:ring-2 focus-within:ring-indigo-500">
                      <h3 className="text-sm font-semibold text-gray-800">
                        <span className="absolute inset-0" aria-hidden="true" />
                        {order.topic}
                      </h3>
                      <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                        ID: {order.id} • Date: {order.date}
                      </p>
                      <div className="mt-2 flex items-center">
                        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                          order.status === 'Delivered' ? 'bg-green-50 text-green-700 ring-green-600/20' : 'bg-blue-50 text-blue-700 ring-blue-600/20'
                        }`}>
                          {order.status}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Brief Submission Form */}
      {showForm && (
        <div className="mt-10 overflow-hidden rounded-lg bg-white shadow ring-1 ring-gray-900/5">
          <div className="p-6">
            <h3 className="text-base font-semibold leading-6 text-gray-900">Submit New Video Brief</h3>
            <form className="mt-6 space-y-6">
              <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
                <div className="sm:col-span-4">
                  <label htmlFor="topic" className="block text-sm font-medium leading-6 text-gray-900">
                    Topic Title
                  </label>
                  <div className="mt-2">
                    <input
                      type="text"
                      name="topic"
                      id="topic"
                      className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                      placeholder="e.g. The Science of Black Holes"
                    />
                  </div>
                </div>

                <div className="col-span-full">
                  <label htmlFor="details" className="block text-sm font-medium leading-6 text-gray-900">
                    Specific Details / Angle
                  </label>
                  <div className="mt-2">
                    <textarea
                      id="details"
                      name="details"
                      rows={3}
                      className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                      placeholder="Describe what you want to cover, specific events, or the scientific angle."
                    />
                  </div>
                </div>

                <div className="col-span-full">
                  <label htmlFor="references" className="block text-sm font-medium leading-6 text-gray-900">
                    References / Sources (optional)
                  </label>
                  <div className="mt-2">
                    <textarea
                      id="references"
                      name="references"
                      rows={2}
                      className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                      placeholder="Links to articles, books, or papers you'd like us to use."
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-x-6">
                <button
                  type="submit"
                  className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                >
                  Submit Brief
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
