import { useState } from "react";

interface PaginationState {
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  reset: () => void;
}

export function usePagination(initialPageSize = 20): PaginationState {
  const [page, setPageState] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  return {
    page,
    pageSize,
    setPage: (p) => setPageState(Math.max(1, p)),
    setPageSize: (s) => {
      setPageSize(s);
      setPageState(1);
    },
    reset: () => setPageState(1),
  };
}
