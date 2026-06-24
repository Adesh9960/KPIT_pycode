from .CANFrame import CANFrame
class RingBuffer:
    _buffer: list
    _capacity: int
    _head: int
    _tail: int
    _count: int
    _captured_tail: int
    def __init__(self, _capacity):
        self._capacity = _capacity
        self._buffer = list()
        self._head = -1
        self._tail = -1
        self._count = 0
        self._captured_tail = -1
        self._buffer = [None] * self._capacity
    
    def push(self, frame: CANFrame):
        if(self.is_empty()):
            self._buffer[0] = frame
            self._head = 0
            self._tail = 0
            self._count += 1
            return
        if not self.is_full(): self._count += 1
        self._tail = (self._tail + 1) % self._capacity
        if(self._tail == self._head):
            self._head = (self._head + 1) % self._capacity
        
        self._buffer[self._tail] = frame

        if(self._tail == self._captured_tail):
            self._captured_tail = -1

    def get_all(self):
        self._captured_tail = self._tail
        if(self._head > self._tail):
            return self._buffer[self._head:] + self._buffer[:self._tail + 1]
        return self._buffer[self._head: self._tail + 1]

    def commit(self):
        deleted_count = 0
        if self._captured_tail == -1 or self._captured_tail == self._tail: deleted_count = self._count
        else: deleted_count = (self._captured_tail - self._head + self._capacity) % self._capacity
        self._count -= deleted_count
        if self._count == 0:
            self._head = -1
            self._tail = -1
            return
        self._head = (self._captured_tail + 1) % self._capacity

    def is_empty(self)->bool:
        return self._count == 0
    
    def is_full(self)->bool:
        return self._count == self._capacity
    
    def size(self)->int:
        return self._count
