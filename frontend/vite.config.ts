import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({plugins:[react()],server:{port:5173,proxy:{'/apply':'http://localhost:8000','/runs':'http://localhost:8000','/events':{target:'http://localhost:8000',changeOrigin:true},'/health':'http://localhost:8000'}}})
