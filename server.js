import express from 'express';
import mongoose from 'mongoose';
import os from 'os';

const app = express();
app.use(express.json());

// Connect to the shared MongoDB container
mongoose.connect('mongodb+srv://suyashmarkandiwar2006_db_user:c4vfEI0RYfrjx6lC@cluster0.o2zsn7a.mongodb.net/?appName=Cluster0')
    .then(() => console.log('Connected to MongoDB'))
    .catch(err => console.error(err));

// Create a simple User schema
const UserSchema = new mongoose.Schema({ name: String, role: String }, { timestamps: true });
const User = mongoose.model('User', UserSchema);

app.get('/', (req, res) => {
    console.log(`Traffic received on ${os.hostname()}`);
    res.json({
        message: "API Request Successful!",
        serverID: os.hostname(),
        dbStatus: mongoose.connection.readyState === 1 ? "Connected" : "Disconnected"
    });
});

// POST: Save a new user to MongoDB
app.post('/add-user', async (req, res) => {
    console.log(`Traffic received on ${os.hostname()}`);
    const newUser = new User({ name: req.body.name, role: req.body.role });
    await newUser.save();
    res.json({ message: 'User saved to database!', serverID: os.hostname() });
});

// GET: Health check — server status, uptime, memory
app.get('/health', (req, res) => {
    try {
        const memUsage = process.memoryUsage();
        res.json({
            status: 'OK',
            serverID: os.hostname(),
            uptime: `${Math.floor(process.uptime())}s`,
            memory: {
                heapUsed: `${(memUsage.heapUsed / 1024 / 1024).toFixed(2)} MB`,
                heapTotal: `${(memUsage.heapTotal / 1024 / 1024).toFixed(2)} MB`,
                rss: `${(memUsage.rss / 1024 / 1024).toFixed(2)} MB`
            },
            dbStatus: mongoose.connection.readyState === 1 ? 'Connected' : 'Disconnected'
        });
    } catch (error) {
        res.json({
            message: error.message,
            status: 'ERROR',
            serverID: os.hostname(),
            dbStatus: mongoose.connection.readyState === 1 ? 'Connected' : 'Disconnected'
        });
    }
});

// GET: Retrieve all users from MongoDB
app.get('/users', async (req, res) => {
    console.log(`Traffic received on ${os.hostname()}`);
    const users = await User.find();
    res.json({ users, serverID: os.hostname() });
});

app.delete('/users', async (req, res) => {
    const users = await User.deleteMany();
    if (!users) {
        return res.json({ message: 'No users found!', serverID: os.hostname() });
    }
    res.json({ message: `${users.deletedCount} users deleted successfully!`, serverID: os.hostname() });
})

app.listen(3000, () => console.log('Server started on port 3000'));