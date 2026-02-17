import { useState, useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'
import Joystick from './components/Joystick'
import MotorStatus from './components/MotorStatus'

const socket = io()

export default function App() {
    const [connected, setConnected] = useState(false)
    const [motorA, setMotorA] = useState({ direction: 'stop', speed: 0 })
    const [motorB, setMotorB] = useState({ direction: 'stop', speed: 0 })
    const [direction, setDirection] = useState('IDLE')

    useEffect(() => {
        socket.on('connect', () => {
            setConnected(true)
            console.log('🔌 Connected to server')
        })

        socket.on('disconnect', () => {
            setConnected(false)
            console.log('🔌 Disconnected from server')
        })

        socket.on('motor_status', (data) => {
            if (data.motor_a) setMotorA(data.motor_a)
            if (data.motor_b) setMotorB(data.motor_b)
        })

        return () => {
            socket.off('connect')
            socket.off('disconnect')
            socket.off('motor_status')
        }
    }, [])

    const getDirection = useCallback((x, y) => {
        if (Math.abs(x) < 10 && Math.abs(y) < 10) return 'IDLE'
        const angle = Math.atan2(-y, x) * (180 / Math.PI)
        if (angle > -22.5 && angle <= 22.5) return 'RIGHT'
        if (angle > 22.5 && angle <= 67.5) return 'FORWARD-RIGHT'
        if (angle > 67.5 && angle <= 112.5) return 'FORWARD'
        if (angle > 112.5 && angle <= 157.5) return 'FORWARD-LEFT'
        if (angle > 157.5 || angle <= -157.5) return 'LEFT'
        if (angle > -157.5 && angle <= -112.5) return 'BACKWARD-LEFT'
        if (angle > -112.5 && angle <= -67.5) return 'BACKWARD'
        if (angle > -67.5 && angle <= -22.5) return 'BACKWARD-RIGHT'
        return 'IDLE'
    }, [])

    const handleJoystickMove = useCallback(({ x, y }) => {
        socket.emit('joystick', { x, y })
        setDirection(getDirection(x, y))
    }, [getDirection])

    const handleJoystickRelease = useCallback(() => {
        socket.emit('joystick', { x: 0, y: 0 })
        setDirection('IDLE')
    }, [])

    const handleEmergencyStop = useCallback(() => {
        if (navigator.vibrate) navigator.vibrate(200)
        socket.emit('emergency_stop')
        setMotorA({ direction: 'stop', speed: 0 })
        setMotorB({ direction: 'stop', speed: 0 })
        setDirection('IDLE')
    }, [])

    return (
        <>
            <div className="app-bg" />
            <div className="grid-overlay" />
            <div className="app">
                {/* Header */}
                <header className="header">
                    <h1>🏎️ Car Motor Controller</h1>
                    <div className={`connection-badge ${connected ? '' : 'disconnected'}`}>
                        <span className="status-dot" />
                        {connected ? 'WiFi Connected' : 'Disconnected'}
                    </div>
                </header>

                {/* Motor Status Cards */}
                <MotorStatus motorA={motorA} motorB={motorB} />

                {/* Direction Label */}
                <div className="direction-indicator">
                    <span className={`dir-label ${direction !== 'IDLE' ? 'active' : ''}`}>
                        {direction}
                    </span>
                </div>

                {/* Joystick */}
                <Joystick
                    size={240}
                    onMove={handleJoystickMove}
                    onRelease={handleJoystickRelease}
                />

                {/* Special Actions */}
                <div className="actions-grid">
                    <button
                        className="action-btn"
                        onMouseDown={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_left' }) }}
                        onMouseUp={() => socket.emit('stop_action')}
                        onMouseLeave={() => socket.emit('stop_action')}
                        onTouchStart={(e) => { e.preventDefault(); if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_left' }) }}
                        onTouchEnd={(e) => { e.preventDefault(); socket.emit('stop_action') }}
                    >
                        🔄 Spin L
                    </button>
                    <button
                        className="action-btn wiggle"
                        onMouseDown={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'wiggle' }) }}
                        onMouseUp={() => socket.emit('stop_action')}
                        onMouseLeave={() => socket.emit('stop_action')}
                        onTouchStart={(e) => { e.preventDefault(); if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'wiggle' }) }}
                        onTouchEnd={(e) => { e.preventDefault(); socket.emit('stop_action') }}
                    >
                        💃 Wiggle
                    </button>
                    <button
                        className="action-btn"
                        onMouseDown={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_right' }) }}
                        onMouseUp={() => socket.emit('stop_action')}
                        onMouseLeave={() => socket.emit('stop_action')}
                        onTouchStart={(e) => { e.preventDefault(); if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_right' }) }}
                        onTouchEnd={(e) => { e.preventDefault(); socket.emit('stop_action') }}
                    >
                        🔄 Spin R
                    </button>
                </div>

                {/* One-Shot Actions */}
                <div className="actions-grid single-shot">
                    <button
                        className="action-btn full-spin"
                        onClick={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_360' }) }}
                    >
                        🌪️ 360° Spin (2.5s)
                    </button>
                </div>

                {/* Emergency Stop */}
                <div className="emergency-stop">
                    <button
                        id="emergency-stop-btn"
                        className="stop-btn"
                        onClick={handleEmergencyStop}
                    >
                        ⛔ Emergency Stop
                    </button>
                </div>
            </div>
        </>
    )
}
