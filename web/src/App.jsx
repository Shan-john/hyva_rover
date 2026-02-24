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

    // LiDAR state
    const [lidarState, setLidarState] = useState({
        mapping: false,
        navigating: false,
        exploring: false,
        available: false,
    })
    const [mapPoints, setMapPoints] = useState([])
    const [navStatus, setNavStatus] = useState(null)
    const [exploreStatus, setExploreStatus] = useState(null)
    const [poseData, setPoseData] = useState(null)
    const [pathData, setPathData] = useState([])
    const [gridData, setGridData] = useState(null)
    const mapCanvasRef = useRef(null)

    // Map management
    const [savedMaps, setSavedMaps] = useState([])
    const [mapName, setMapName] = useState('')
    const [showMapPanel, setShowMapPanel] = useState(false)
    const [exploreMode, setExploreMode] = useState('explore')

    useEffect(() => {
        socket.on('connect', () => {
            setConnected(true)
            console.log('🔌 Connected to server')
            socket.emit('list_maps')
        })

        socket.on('disconnect', () => {
            setConnected(false)
            console.log('🔌 Disconnected from server')
        })

        socket.on('motor_status', (data) => {
            if (data.motor_a) setMotorA(data.motor_a)
            if (data.motor_b) setMotorB(data.motor_b)
        })

        socket.on('lidar_state', (data) => {
            setLidarState(data)
        })

        socket.on('map_data', (data) => {
            if (data.points) {
                setMapPoints(data.points)
            }
        })

        socket.on('nav_status', (data) => {
            setNavStatus(data)
        })

        socket.on('explore_status', (data) => {
            setExploreStatus(data)
        })

        socket.on('grid_update', (data) => {
            if (data.grid) setGridData(data.grid)
            if (data.pose) setPoseData(data.pose)
            if (data.path) setPathData(data.path)
        })

        socket.on('map_list', (data) => {
            setSavedMaps(data || [])
        })

        socket.on('map_saved', (data) => {
            if (!data.error) {
                console.log('Map saved:', data.name)
                socket.emit('list_maps')
            }
        })

        socket.on('map_loaded', (data) => {
            if (!data.error) {
                console.log('Map loaded:', data.name)
            }
        })

        return () => {
            socket.off('connect')
            socket.off('disconnect')
            socket.off('motor_status')
            socket.off('lidar_state')
            socket.off('map_data')
            socket.off('nav_status')
            socket.off('explore_status')
            socket.off('grid_update')
            socket.off('map_list')
            socket.off('map_saved')
            socket.off('map_loaded')
        }
    }, [])

    // Draw radar map on canvas
    useEffect(() => {
        const canvas = mapCanvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const w = canvas.width
        const h = canvas.height
        const cx = w / 2
        const cy = h / 2

        // Clear
        ctx.fillStyle = '#0a0e17'
        ctx.fillRect(0, 0, w, h)

        // Draw occupancy grid if available
        if (gridData && gridData.grid) {
            const grid = gridData.grid
            const rows = grid.length
            const cols = rows > 0 ? grid[0].length : 0
            const origin = gridData.origin || Math.floor(rows / 2)
            const cellPx = Math.min(w, h) / rows

            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const v = grid[r][c]
                    if (v === 0) continue // skip unknown (already dark)
                    const px = c * cellPx
                    const py = r * cellPx
                    if (v === 1) {
                        ctx.fillStyle = 'rgba(15,20,40,0.8)' // free = very dark blue
                    } else if (v === 100) {
                        ctx.fillStyle = 'rgba(200,210,230,0.9)' // wall = white
                    }
                    ctx.fillRect(px, py, cellPx + 0.5, cellPx + 0.5)
                }
            }
        }

        // Scale for scan points
        let maxDist = 0
        for (const p of mapPoints) {
            if (p.distance > maxDist) maxDist = p.distance
        }
        const scale = maxDist > 0 ? (Math.min(cx, cy) - 20) / maxDist : 20

        // Draw grid circles (only if no occupancy grid)
        if (!gridData) {
            const ringCount = 4
            for (let i = 1; i <= ringCount; i++) {
                const r = (i / ringCount) * (Math.min(cx, cy) - 10)
                ctx.beginPath()
                ctx.arc(cx, cy, r, 0, Math.PI * 2)
                ctx.strokeStyle = 'rgba(99,102,241,0.12)'
                ctx.lineWidth = 1
                ctx.stroke()
                const dist = ((i / ringCount) * maxDist).toFixed(1)
                ctx.fillStyle = 'rgba(148,163,184,0.5)'
                ctx.font = '10px Inter, sans-serif'
                ctx.fillText(`${dist}m`, cx + r - 20, cy - 4)
            }
        }

        // Crosshair
        ctx.strokeStyle = 'rgba(99,102,241,0.08)'
        ctx.beginPath()
        ctx.moveTo(cx, 0); ctx.lineTo(cx, h)
        ctx.moveTo(0, cy); ctx.lineTo(w, cy)
        ctx.stroke()

        // Draw path trail
        if (pathData.length > 1) {
            ctx.beginPath()
            ctx.strokeStyle = 'rgba(168,85,247,0.4)'
            ctx.lineWidth = 1.5
            for (let i = 0; i < pathData.length; i++) {
                const px = cx + pathData[i].x * scale
                const py = cy - pathData[i].y * scale
                if (i === 0) ctx.moveTo(px, py)
                else ctx.lineTo(px, py)
            }
            ctx.stroke()
        }

        // Draw sector indicators if navigating
        if (navStatus && navStatus.sector_distances && navStatus.sector_distances.length > 0) {
            const sectorCount = navStatus.sector_distances.length
            const sectorWidth = (2 * Math.PI) / sectorCount
            navStatus.sector_distances.forEach((d, i) => {
                const angle = ((i * 360 / sectorCount) - 180) * Math.PI / 180
                const r = d > 0 ? Math.min(d * scale, Math.min(cx, cy) - 10) : 0
                if (r > 0) {
                    ctx.beginPath()
                    ctx.moveTo(cx, cy)
                    ctx.arc(cx, cy, r, angle - sectorWidth / 2, angle + sectorWidth / 2)
                    ctx.closePath()
                    const isBest = i === navStatus.best_sector
                    ctx.fillStyle = isBest
                        ? 'rgba(16,185,129,0.15)'
                        : 'rgba(34,211,238,0.05)'
                    ctx.fill()
                }
            })
        }

        // Draw scan points
        for (const p of mapPoints) {
            const px = cx + p.x * scale
            const py = cy - p.y * scale
            const isClose = p.distance < 0.35
            ctx.beginPath()
            ctx.arc(px, py, isClose ? 3 : 2, 0, Math.PI * 2)
            ctx.fillStyle = isClose
                ? 'rgba(239,68,68,0.9)'
                : 'rgba(34,211,238,0.7)'
            ctx.fill()
        }

        // Car icon at centre
        ctx.beginPath()
        ctx.arc(cx, cy, 6, 0, Math.PI * 2)
        ctx.fillStyle = '#6366f1'
        ctx.fill()
        ctx.strokeStyle = '#a855f7'
        ctx.lineWidth = 2
        ctx.stroke()

        // Forward direction triangle
        ctx.beginPath()
        ctx.moveTo(cx, cy - 14)
        ctx.lineTo(cx - 5, cy - 8)
        ctx.lineTo(cx + 5, cy - 8)
        ctx.closePath()
        ctx.fillStyle = '#6366f1'
        ctx.fill()

    }, [mapPoints, navStatus, gridData, pathData])

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
        setNavStatus(null)
        setExploreStatus(null)
    }, [])

    // LiDAR controls
    const toggleMapping = useCallback(() => {
        if (navigator.vibrate) navigator.vibrate(50)
        if (lidarState.mapping) {
            socket.emit('stop_mapping')
        } else {
            socket.emit('start_mapping')
        }
    }, [lidarState.mapping])

    const toggleNavigation = useCallback(() => {
        if (navigator.vibrate) navigator.vibrate(50)
        if (lidarState.navigating) {
            socket.emit('stop_navigation')
        } else {
            socket.emit('start_navigation')
        }
    }, [lidarState.navigating])

    const toggleExploration = useCallback(() => {
        if (navigator.vibrate) navigator.vibrate(50)
        if (lidarState.exploring) {
            socket.emit('stop_exploration')
        } else {
            socket.emit('start_exploration', { mode: exploreMode })
        }
    }, [lidarState.exploring, exploreMode])

    const handleSaveMap = useCallback(() => {
        const name = mapName.trim() || `Room ${savedMaps.length + 1}`
        socket.emit('save_map', { name })
        setMapName('')
    }, [mapName, savedMaps.length])

    const handleLoadMap = useCallback((name) => {
        socket.emit('load_map', { name })
    }, [])

    const handleDeleteMap = useCallback((name) => {
        if (confirm(`Delete map "${name}"?`)) {
            socket.emit('delete_map', { name })
        }
    }, [])

    const handleReturnToStart = useCallback(() => {
        if (navigator.vibrate) navigator.vibrate(50)
        socket.emit('return_to_start')
    }, [])

    const handleModeChange = useCallback((mode) => {
        setExploreMode(mode)
        if (lidarState.exploring) {
            socket.emit('set_explore_mode', { mode })
        }
    }, [lidarState.exploring])

    const isAnyActive = lidarState.mapping || lidarState.navigating || lidarState.exploring

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

                {/* LiDAR Section */}
                <div className="lidar-section">
                    <div className="lidar-header">
                        <span className="lidar-title">📡 LiDAR & Navigation</span>
                        <span className={`lidar-badge ${lidarState.available ? 'online' : 'offline'}`}>
                            {lidarState.available ? 'ONLINE' : 'OFFLINE'}
                        </span>
                    </div>

                    {/* Map Canvas */}
                    <div className="map-canvas-container">
                        <canvas
                            ref={mapCanvasRef}
                            width={320}
                            height={320}
                            className="map-canvas"
                        />
                        {mapPoints.length === 0 && !gridData && (
                            <div className="map-placeholder">
                                <span>📡</span>
                                <p>Press a button below to start</p>
                            </div>
                        )}
                        {navStatus && (
                            <div className="nav-overlay">
                                <span className={`nav-action ${navStatus.action}`}>
                                    {navStatus.action === 'forward' && '⬆️ FORWARD'}
                                    {navStatus.action === 'turn_left' && '⬅️ TURN LEFT'}
                                    {navStatus.action === 'turn_right' && '➡️ TURN RIGHT'}
                                    {navStatus.action === 'stop' && '⛔ BLOCKED'}
                                </span>
                            </div>
                        )}
                        {/* Exploration progress overlay */}
                        {exploreStatus && (
                            <div className="explore-overlay">
                                <div className="explore-progress-bar">
                                    <div
                                        className="explore-progress-fill"
                                        style={{ width: `${exploreStatus.explored_pct || 0}%` }}
                                    />
                                </div>
                                <span className="explore-pct">
                                    {(exploreStatus.explored_pct || 0).toFixed(1)}% mapped
                                </span>
                                {exploreStatus.complete && <span className="explore-done">✅ Complete</span>}
                            </div>
                        )}
                        {/* Pose info */}
                        {poseData && (
                            <div className="pose-info">
                                <span>📍 ({poseData.x?.toFixed(2)}, {poseData.y?.toFixed(2)}) {poseData.heading?.toFixed(0)}°</span>
                            </div>
                        )}
                    </div>

                    {/* Exploration Mode Selector */}
                    <div className="mode-selector">
                        {[
                            { id: 'explore', label: '🔍 Explore', tip: 'Auto-discover' },
                            { id: 'coverage', label: '📐 Coverage', tip: 'Grid sweep' },
                            { id: 'boundary', label: '🔲 Boundary', tip: 'Follow walls' },
                            { id: 'corners', label: '📌 Corners', tip: 'Visit corners' },
                        ].map(m => (
                            <button
                                key={m.id}
                                className={`mode-btn ${exploreMode === m.id ? 'active' : ''}`}
                                onClick={() => handleModeChange(m.id)}
                                title={m.tip}
                            >
                                {m.label}
                            </button>
                        ))}
                    </div>

                    {/* Main LiDAR Buttons */}
                    <div className="lidar-buttons">
                        <button
                            className={`lidar-btn explore-btn ${lidarState.exploring ? 'active' : ''}`}
                            onClick={toggleExploration}
                            disabled={lidarState.mapping || lidarState.navigating}
                            id="explore-room-btn"
                        >
                            <span className="lidar-btn-icon">🔍</span>
                            <span>{lidarState.exploring ? 'Stop Exploring' : 'Explore Room'}</span>
                        </button>
                        <button
                            className={`lidar-btn map-btn ${lidarState.mapping ? 'active' : ''}`}
                            onClick={toggleMapping}
                            disabled={lidarState.exploring || lidarState.navigating}
                            id="map-surroundings-btn"
                        >
                            <span className="lidar-btn-icon">🗺️</span>
                            <span>{lidarState.mapping ? 'Stop Mapping' : 'Map Surroundings'}</span>
                        </button>
                    </div>

                    <div className="lidar-buttons">
                        <button
                            className={`lidar-btn nav-btn ${lidarState.navigating ? 'active' : ''}`}
                            onClick={toggleNavigation}
                            disabled={lidarState.exploring || lidarState.mapping}
                            id="run-path-btn"
                        >
                            <span className="lidar-btn-icon">🚗</span>
                            <span>{lidarState.navigating ? 'Stop Navigation' : 'Run Path'}</span>
                        </button>
                        <button
                            className="lidar-btn return-btn"
                            onClick={handleReturnToStart}
                            disabled={!lidarState.exploring}
                        >
                            <span className="lidar-btn-icon">🏠</span>
                            <span>Return Home</span>
                        </button>
                    </div>

                    {/* Map Management */}
                    <div className="map-management">
                        <button
                            className="map-toggle-btn"
                            onClick={() => setShowMapPanel(!showMapPanel)}
                        >
                            💾 Saved Maps ({savedMaps.length}) {showMapPanel ? '▲' : '▼'}
                        </button>

                        {showMapPanel && (
                            <div className="map-panel">
                                <div className="map-save-row">
                                    <input
                                        type="text"
                                        placeholder="Map name..."
                                        value={mapName}
                                        onChange={(e) => setMapName(e.target.value)}
                                        className="map-name-input"
                                    />
                                    <button
                                        className="map-save-btn"
                                        onClick={handleSaveMap}
                                        disabled={!isAnyActive && mapPoints.length === 0}
                                    >
                                        💾 Save
                                    </button>
                                </div>
                                {savedMaps.length === 0 ? (
                                    <p className="map-empty">No saved maps yet</p>
                                ) : (
                                    <ul className="map-list">
                                        {savedMaps.map((m, i) => (
                                            <li key={i} className="map-item">
                                                <span className="map-item-name">{m.name}</span>
                                                <span className="map-item-stats">
                                                    {m.stats?.explored_pct?.toFixed(0)}%
                                                </span>
                                                <button
                                                    className="map-action-btn load"
                                                    onClick={() => handleLoadMap(m.name)}
                                                >
                                                    📂
                                                </button>
                                                <button
                                                    className="map-action-btn delete"
                                                    onClick={() => handleDeleteMap(m.name)}
                                                >
                                                    🗑️
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}
                    </div>
                </div>

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
                <div className="actions-grid single-shot half-split">
                    <button
                        className="action-btn half-spin"
                        onClick={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_180' }) }}
                    >
                        💫 180° Spin
                    </button>
                    <button
                        className="action-btn full-spin"
                        onClick={() => { if (navigator.vibrate) navigator.vibrate(50); socket.emit('start_action', { type: 'spin_360' }) }}
                    >
                        🌪️ 360° Spin
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
            </div>
        </>
    )
}
