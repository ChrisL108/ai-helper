const express = require('express');
const bodyParser = require('body-parser');
const OpenAIApi = require("openai");

const app = express();
const port = 3000;

app.use(bodyParser.json());
app.use(express.static('public'));

async function aiStuff() {

    const openai = new OpenAIApi();

    try {
        // const { text } = req.body;
        const completion = await openai.chat.completions.create({
            model: "gpt-4o-mini",
            messages: [
                { role: "system", content: "You are a helpful assistant." },
                {
                    role: "user",
                    content: "Write a haiku about recursion in programming.",
                },
            ],
        });

        console.log(JSON.stringify(completion, null, 3));
        console.log(completion.choices[0].message);
        // res.json({ response: completion.data.choices[0].message.content });
        // res.json({ response: "yo yo yo" });
    } catch (error) {
        console.error('Error:', error);
        // res.status(500).json({ error: 'An error occurred while processing the request.' });
    }
}

aiStuff();
// app.post('/process-audio', async (req, res) => {
// });

// app.listen(port, () => {
//     console.log(`Server running at http://localhost:${port}`);
// });