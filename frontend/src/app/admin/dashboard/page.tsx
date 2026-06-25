'use client';

import { useState } from 'react';

type OrderStatus = 'Received' | 'Researching' | 'Scripting' | 'Production' | 'Rendering' | 'Delivered';

interface Order {
  id: string;
  customer: string;
  topic: string;
  status: OrderStatus;
  date: string;
}

export default function AdminDashboard() {
  const [orders, setOrders] = useState<Order[]>([
    {
      id: 'ORD001',
      customer: 'jane@example.com',
      topic: 'The Fall of Constantinople',
      status: 'Delivered',
      date: '2024-06-01',
    },
    {
      id: 'ORD002',
      customer: 'john@example.com',
      topic: 'Quantum Entanglement Explained',
      status: 'Production',
      date: '2024-06-15',
    },
    {
      id: 'ORD003',
      customer: 'sarah@example.com',
      topic: 'The Industrial Revolution',
      status: 'Researching',
      date: '2024-06-20',
    },
  ]);

  const stats = {
    deliveredThisMonth: orders.filter(o => o.status === 'Delivered').length,
    pendingOrders: orders.filter(o => o.status !== 'Delivered').length,
    activeSubscribers: 124, // Mock
  };

  const statusOptions: OrderStatus[] = [
    'Received',
    'Researching',
    'Scripting',
    'Production',
    'Rendering',
    'Delivered',
  ];

  const handleStatusChange = (orderId: string, newStatus: OrderStatus) => {
    setOrders(orders.map(order => 
      order.id === orderId ? { ...order, status: newStatus } : order
    ));
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Admin Dashboard
          </h2>
        </div>
      </div>

      {/* Stats Section */}
      <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6">
          <dt className="truncate text-sm font-medium text-gray-500">Delivered This Month</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight text-indigo-600">{stats.deliveredThisMonth}</dd>
        </div>
        <div className="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6">
          <dt className="truncate text-sm font-medium text-gray-500">Pending Orders</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight text-indigo-600">{stats.pendingOrders}</dd>
        </div>
        <div className="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6">
          <dt className="truncate text-sm font-medium text-gray-500">Active Subscribers</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight text-indigo-600">{stats.activeSubscribers}</dd>
        </div>
      </div>

      {/* Orders Management Table */}
      <div className="mt-10 bg-white shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold leading-6 text-gray-900">Order Management</h3>
          <p className="mt-1 text-sm text-gray-500">Update the status of current documentary projects.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">OrderID</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Customer</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Topic</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Status</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Date</th>
                <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">{order.id}</td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{order.customer}</td>
                  <td className="px-3 py-4 text-sm text-gray-500">{order.topic}</td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    <select
                      value={order.status}
                      onChange={(e) => handleStatusChange(order.id, e.target.value as OrderStatus)}
                      className="rounded-md border-gray-300 py-1 pl-2 pr-8 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                    >
                      {statusOptions.map((status) => (
                        <option key={status} value={status}>{status}</option>
                      ))}
                    </select>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{order.date}</td>
                  <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button className="text-indigo-600 hover:text-indigo-900">Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
