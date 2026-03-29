import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useBooksStore = defineStore('books', () => {
  const books = ref([])
  const loading = ref(false)
  const genres = ref([])

  async function fetchBooks(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/books/', { params })
      books.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchGenres() {
    try {
      const { data } = await api.get('/books/genres')
      genres.value = data
    } catch {
      genres.value = []
    }
  }

  async function addBook(bookData) {
    const { data } = await api.post('/books/', bookData)
    books.value.unshift(data)
    return data
  }

  async function getBook(id) {
    const { data } = await api.get(`/books/${id}`)
    return data
  }

  async function updateBook(id, bookData) {
    const { data } = await api.put(`/books/${id}`, bookData)
    const idx = books.value.findIndex((b) => b.id === id)
    if (idx !== -1) books.value[idx] = data
    return data
  }

  async function updateReadingStatus(id, readingStatus) {
    const { data } = await api.patch(`/books/${id}/status`, { reading_status: readingStatus })
    const idx = books.value.findIndex((b) => b.id === id)
    if (idx !== -1) books.value[idx] = data
    return data
  }

  async function deleteBook(id) {
    await api.delete(`/books/${id}`)
    books.value = books.value.filter((b) => b.id !== id)
  }

  return { books, loading, genres, fetchBooks, fetchGenres, addBook, getBook, updateBook, updateReadingStatus, deleteBook }
})
