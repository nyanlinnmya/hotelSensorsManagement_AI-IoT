import React, { useEffect, useState } from 'react';
import { supabase } from './supabaseClient';
import { PieChart, Pie, Cell } from 'recharts';

const STATUS_COLORS = {
  healthy: 'green',
  warning: 'orange',
  critical: 'red'
};

const METERS = ['temperature', 'humidity', 'co2'];

function RoomCard({ room, data }) {
  const statusColor = STATUS_COLORS[data.health_status] || 'gray';

  return (
    <div style={{
      border: `2px solid ${statusColor}`,
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '16px',
      width: '300px',
      background: '#f9f9f9'
    }}>
      <h3>{room}</h3>
      <p>Status: <strong style={{ color: statusColor }}>{data.health_status}</strong></p>
      <p>Occupancy: <strong>{data.is_occupied ? 'Occupied' : 'Vacant'}</strong></p>
      <p>Datapoint: {data.datapoint}</p>

      {METERS.includes(data.datapoint) && (
        <PieChart width={150} height={150}>
          <Pie
            dataKey="value"
            startAngle={180}
            endAngle={0}
            data={[{ name: data.datapoint, value: 100 }]}
            cx="50%"
            cy="100%"
            innerRadius={40}
            outerRadius={60}
            fill="#8884d8"
            label={() => `${data.datapoint}: ${data.health_status}`}
          >
            <Cell fill={statusColor} />
          </Pie>
        </PieChart>
      )}
    </div>
  );
}

function Dashboard() {
  const [roomData, setRoomData] = useState({});

  useEffect(() => {
    fetchRoomStates();
    console.log("fetchRoomStates called");
    const channel = supabase
      .channel('room_updates')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'room_states' },
        payload => {
          const data = payload.new;
          setRoomData(prev => ({
            ...prev,
            [data.room_id + '-' + data.datapoint]: data
          }));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const fetchRoomStates = async () => {
    const { data, error } = await supabase.from('room_states').select('*');
    if (!error) {
      const formatted = {};
      data.forEach(row => {
        formatted[row.room_id + '-' + row.datapoint] = row;
      });
      setRoomData(formatted);
    }
  };

  const groupedByRoom = Object.values(roomData).reduce((acc, row) => {
    if (!acc[row.room_id]) acc[row.room_id] = [];
    acc[row.room_id].push(row);
    return acc;
  }, {});

  return (
    <div style={{ padding: '20px' }}>
      <h1>Hotel Room Dashboard</h1>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {Object.entries(groupedByRoom).map(([room_id, datapoints]) => (
          <div key={room_id}>
            <h2>{room_id}</h2>
            {datapoints.map(dp => (
              <RoomCard key={dp.datapoint} room={room_id} data={dp} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
