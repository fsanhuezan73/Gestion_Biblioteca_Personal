import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/utils/api'

export const useBooksStore = defineStore('books', () => {
  const books = ref([])
  const loading = ref(false)

  async function fetchBooks() {
    loading.value = true
    try {
      const { data } = await api.get('/books/')
      books.value = data
    } finally {
      loading.value = false
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

  async function deleteBook(id) {
    await api.delete(`/books/${id}`)
    books.value = books.value.filter((b) => b.id !== id)
  }

  return { books, loading, fetchBooks, addBook, getBook, updateBook, deleteBook }
})
